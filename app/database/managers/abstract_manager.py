import logging
import uuid
from uuid import UUID
from contextlib import contextmanager
from abc import ABC, abstractmethod
from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import inspect
from app.database.db_globals import Session

logger = logging.getLogger('ok_service')

EXACT_MATCH_FIELDS = {"status", "role", "category"}


class BaseDBManager(ABC):
    @property
    @abstractmethod
    def model(self):
        """Метод, который возвращает модель (таблицу) для работы."""

    @contextmanager
    def session_scope(self):
        """Контекстный менеджер для управления сессией с логированием."""
        session = Session()
        try:
            # logger.debug("Начало сессии", extra={"login": "database"})
            yield session
            if session.is_active:
                session.commit()
        except Exception as e:
            if session.is_active:
                session.rollback()
            logger.error(f"Ошибка в сессии: {e}", extra={"login": "database"})
            raise
        finally:
            if session.is_active:
                session.close()

    def add(self, **kwargs):
        try:
            with self.session_scope() as session:
                new_record = self.model(**kwargs)
                session.add(new_record)
                try:
                    session.flush()
                except Exception:
                    session.rollback()
                    raise
                return new_record.to_dict()
        except Exception as e:
            logger.error(f"""Ошибка при добавлении записи: {
                         e}""", extra={"login": "database"})
            raise

    def get_by_id(self, record_id):
        """Получение записи по ID (по первичному ключу)."""
        try:
            logger.debug(f"Получение записи по ID: {record_id}", extra={
                         "login": "database"})
            with self.session_scope() as session:
                primary_key = inspect(self.model).primary_key
                if not primary_key:
                    raise ValueError(
                        f"No primary key found for model {self.model.__name__}")

                primary_key_name = primary_key[0].name
                record = session.query(self.model).filter(
                    getattr(self.model, primary_key_name) == record_id).first()

                if record:
                    logger.info(f"Запись найдена: {record.to_dict()}", extra={
                                "login": "database"})
                    return record.to_dict()
                logger.warning(f"Запись с ID {record_id} не найдена", extra={
                               "login": "database"})
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении записи по ID: {e}", extra={
                         "login": "database"})
            raise

    def get_all(self, offset=0, limit=None):
        """Получение всех записей с поддержкой пагинации."""
        try:
            logger.debug(f"Получение всех записей, offset={offset}, limit={limit}", extra={
                         "login": "database"})
            with self.session_scope() as session:
                records = session.query(self.model).offset(
                    offset).limit(limit).all()
                result = [record.to_dict() for record in records]
                logger.info(f"Найдено {len(result)} записей", extra={
                            "login": "database"})
                return result
        except Exception as e:
            logger.error(f"Ошибка при получении всех записей: {e}", extra={
                         "login": "database"})
            raise

    def get_record_by_id(self, record_id):
        """Получение записи по ID в виде объекта."""
        try:
            logger.info("Fetching record by ID: %s",
                        record_id, extra={"login": "database"})
            with self.session_scope() as session:
                primary_key = inspect(self.model).primary_key
                if not primary_key:
                    raise ValueError(
                        f"No primary key found for model {self.model.__name__}")

                primary_key_name = primary_key[0].name
                record = session.query(self.model).filter(
                    getattr(self.model, primary_key_name) == record_id).first()
                if record:
                    logger.info("Record found: %s", record,
                                extra={"login": "database"})
                    return record
                logger.warning("Record not found by ID: %s",
                               record_id, extra={"login": "database"})
                return None
        except Exception as e:
            logger.error("Error fetching record by ID: %s",
                         e, extra={"login": "database"})
            raise

    def get_count(self):
        """Получение общего количества записей."""
        try:
            logger.info("Counting records in table",
                        extra={"login": "database"})
            with self.session_scope() as session:
                count = session.query(self.model).count()
                logger.info("Total records count: %d", count,
                            extra={"login": "database"})
                return count
        except Exception as e:
            logger.error("Error counting records: %s",
                         e, extra={"login": "database"})
            raise

    def update(self, record_id, **kwargs):
        """Обновление записи по ID, игнорируя None в аргументах."""
        try:
            # Убираем None из kwargs
            filtered_kwargs = {key: value for key,
                               value in kwargs.items() if value is not None}

            if not filtered_kwargs:
                logger.warning("No valid fields provided for update: %s",
                               kwargs, extra={"login": "database"})
                return None

            logger.info("Updating record with ID: %s, fields: %s",
                        record_id, filtered_kwargs, extra={"login": "database"})
            with self.session_scope() as session:
                primary_key = inspect(self.model).primary_key[0].name
                record = session.query(self.model).filter(
                    getattr(self.model, primary_key) == record_id).first()
                if record:
                    for key, value in filtered_kwargs.items():
                        setattr(record, key, value)
                        flag_modified(record, key)
                    logger.info("Record updated successfully: %s",
                                record, extra={"login": "database"})
                    return record
                else:
                    logger.warning("Record not found for update: %s",
                                   record_id, extra={"login": "database"})
                    return None
        except Exception as e:
            logger.error("Error updating record with ID %s: %s",
                         record_id, e, extra={"login": "database"})
            raise

    def delete(self, record_id):
        """Удаление записи по ID с обработкой зависимости."""
        try:
            logger.info("Deleting record with ID: %s",
                        record_id, extra={"login": "database"})
            with self.session_scope() as session:
                record = self.get_record_by_id(record_id)
                if record:
                    session.delete(record)
                    logger.info("Record deleted successfully: %s",
                                record, extra={"login": "database"})
                    return record
                else:
                    logger.warning("Record not found for deletion: %s",
                                   record_id, extra={"login": "database"})
                    return None
        except IntegrityError as e:
            logger.error("Cannot delete record %s due to integrity constraint: %s",
                         record_id, e, extra={"login": "database"})
            raise IntegrityError(
                "Cannot delete record: dependent data exists.") from e

        except Exception as e:
            logger.error("Error deleting record with ID %s: %s",
                         record_id, e, extra={"login": "database"})
            raise

    def filter_by(self, **kwargs):
        """Фильтрация записей по заданным критериям."""
        try:
            logger.info("Filtering records by criteria: %s",
                        kwargs, extra={"login": "database"})
            with self.session_scope() as session:
                records = session.query(self.model).filter_by(**kwargs).all()
                logger.info("Found %d records", len(records),
                            extra={"login": "database"})
                return records
        except Exception as e:
            logger.error("Error filtering records by criteria %s: %s",
                         kwargs, e, extra={"login": "database"})
            raise

    def filter_by_dict(self, **kwargs):
        """Фильтрация записей с преобразованием объектов в словари."""
        try:
            logger.info("Filtering records by criteria and converting to dict: %s", kwargs, extra={
                        "login": "database"})
            with self.session_scope() as session:
                records = session.query(self.model).filter_by(**kwargs).all()
                result = [record.to_dict() for record in records]
                logger.info("Found %d records", len(result),
                            extra={"login": "database"})
                return result
        except Exception as e:
            logger.error("Error filtering records by criteria %s: %s",
                         kwargs, e, extra={"login": "database"})
            raise

    def filter_one_by_dict(self, **kwargs):
        """Фильтрация записей с ожиданием одного результата, возвращаем словарь или None."""
        try:
            logger.info("Filtering one record by criteria and converting to dict: %s", kwargs, extra={
                        "login": "database"})
            with self.session_scope() as session:
                record = session.query(self.model).filter_by(**kwargs).first()
                if record:
                    logger.info("Record found: %s", record,
                                extra={"login": "database"})
                    return record.to_dict()
                logger.warning("No record found for criteria: %s",
                               kwargs, extra={"login": "database"})
                return None
        except Exception as e:
            logger.error("Error filtering one record by criteria %s: %s",
                         kwargs, e, extra={"login": "database"})
            raise

    def exists_by_id(self, record_id):
        """Проверяет существование записи по ID."""
        try:
            logger.info("Checking existence of record by ID: %s",
                        record_id, extra={"login": "database"})
            with self.session_scope() as session:
                primary_key = inspect(self.model).primary_key
                if not primary_key:
                    raise ValueError(
                        f"No primary key found for model {self.model.__name__}")

                primary_key_name = primary_key[0].name
                exists = session.query(self.model).filter(
                    getattr(self.model, primary_key_name) == record_id).count() > 0
                logger.info("Record existence: %s", exists,
                            extra={"login": "database"})
                return exists
        except Exception as e:
            logger.error("Error checking existence by ID %s: %s",
                         record_id, e, extra={"login": "database"})
            raise

    def exists(self, **kwargs):
        """Проверяет существование записи с указанными полями."""
        try:
            logger.debug(f"Проверка существования записи: {kwargs}", extra={
                         "login": "database"})
            with self.session_scope() as session:
                exists = session.query(self.model).filter_by(
                    **kwargs).count() > 0
                logger.info(f"Существование записи: {exists}", extra={
                            "login": "database"})
                return exists
        except Exception as e:
            logger.error(f"Ошибка при проверке существования записи: {e}", extra={
                         "login": "database"})
            raise

    def get_all_filtered(self, offset=0, limit=None, sort_by="created_at", sort_order='desc', **filters):
        logger.debug("get_all_filtered вызывается с фильтрацией, сортировкой и пагинацией.",
                     extra={"login": "database"})

        with self.session_scope() as session:

            query = session.query(self.model)

            # Применяем фильтры
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    column = getattr(self.model, key)

                    # Проверяем, является ли значение UUID (обычно 36 символов)
                    if isinstance(value, uuid.UUID) or (isinstance(value, str) and len(value) == 36 and '-' in value):
                        query = query.filter(column == value)
                        logger.debug(f"Применяем точный UUID-фильтр: {key} = {UUID(value)}",
                                     extra={'login': 'database'})

                    # Поля, требующие точного сравнения
                    elif key in EXACT_MATCH_FIELDS:
                        query = query.filter(column == value)
                        logger.debug(f"Применяем точный фильтр для {key}: {key} = {value}",
                                     extra={'login': 'database'})

                    elif isinstance(value, str):
                        value = value.strip()  # Убираем лишние пробелы

                        if "%" not in value:
                            # Добавляем wildcard, если строка достаточно длинная
                            value = f"%{value}%"

                        query = query.filter(column.ilike(value))
                        logger.debug(f"Применяем ILIKE-фильтр: {key} LIKE {value}",
                                     extra={'login': 'database'})

                    else:
                        query = query.filter(column == value)
                        logger.debug(f"Применяем фильтр: {key} = {value}",
                                     extra={'login': 'database'})

            # Применяем сортировку
            if sort_by and hasattr(self.model, sort_by):
                order = desc if sort_order == 'desc' else asc
                query = query.order_by(order(getattr(self.model, sort_by)))
                logger.debug(f"Применяем сортировку: {sort_by} {sort_order}",
                             extra={"login": "database"})

            # Применяем пагинацию
            if offset:
                query = query.offset(offset)
                logger.debug(f"Применяем смещение: offset = {offset}",
                             extra={"login": "database"})
            if limit:
                query = query.limit(limit)
                logger.debug(f"Применяем лимит: limit = {limit}",
                             extra={"login": "database"})

            # Получаем записи
            records = query.all()
            logger.debug(f"Найдено записей: {len(records)}",
                         extra={"login": "database"})

            return [record.to_dict() for record in records]
