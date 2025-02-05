import logging
import uuid
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, asc, desc
from app.database.models import Projects, ProjectSchedules, ProjectWorks, Objects
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager

logger = logging.getLogger('ok_service')

EXACT_MATCH_FIELDS = {"status"}


class ProjectsManager(BaseDBManager):

    @property
    def model(self):
        return Projects

    def get_all_filtered_with_status(self, role, offset=0, limit=None, sort_by=None, sort_order='asc', **filters):
        logger.debug("get_all_filtered_with_status вызывается с фильтрацией, сортировкой и проверкой статуса объекта.",
                     extra={"login": "database"})

        with self.session_scope() as session:
            query = session.query(self.model).options(joinedload(
                Projects.objects))  # Используем joinload для оптимизации

            # Если пользователь — обычный "user", фильтруем проекты по статусу объекта
            if role == "user":
                query = query.join(Objects, Projects.object == Objects.object_id).filter(
                    Objects.status == "active")
                logger.debug("Фильтрация: только проекты с объектами в статусе 'active'.",
                             extra={"login": "database"})

            # Применяем стандартные фильтры из filters
            filter_conditions = []
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    column = getattr(self.model, key)

                    # Проверяем, является ли значение UUID (обычно 36 символов)
                    if isinstance(value, uuid.UUID) or (isinstance(value, str) and len(value) == 36 and '-' in value):
                        filter_conditions.append(column == value)
                        logger.debug(f"Применяем точный UUID-фильтр: {key} = {value}",
                                     extra={'login': 'database'})

                    # Поля, требующие точного сравнения
                    elif key in EXACT_MATCH_FIELDS:
                        filter_conditions.append(column == value)
                        logger.debug(f"Применяем точный фильтр для {key}: {key} = {value}",
                                     extra={'login': 'database'})

                    elif isinstance(value, str):
                        value = value.strip()  # Убираем лишние пробелы

                        if "%" not in value:
                            # Добавляем wildcard для частичного поиска
                            value = f"%{value}%"

                        filter_conditions.append(column.ilike(value))
                        logger.debug(f"Применяем ILIKE-фильтр: {key} LIKE {value}",
                                     extra={'login': 'database'})

                    else:
                        filter_conditions.append(column == value)
                        logger.debug(f"Применяем фильтр: {key} = {value}",
                                     extra={'login': 'database'})

            # Добавляем фильтры в запрос
            if filter_conditions:
                query = query.filter(and_(*filter_conditions))

            # Применяем сортировку
            if sort_by and hasattr(self.model, sort_by):
                order = desc if sort_order == 'desc' else asc
                query = query.order_by(order(getattr(self.model, sort_by)))
                logger.debug(f"Применяем сортировку: {sort_by} {sort_order}",
                             extra={"login": "database"})

            # Применяем пагинацию
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            records = query.all()
            logger.debug(f"Найдено записей: {len(records)}",
                         extra={"login": "database"})

            return [record.to_dict() for record in records]


class ProjectSchedulesManager(BaseDBManager):

    @property
    def model(self):
        return ProjectSchedules


class ProjectWorksManager(BaseDBManager):

    @property
    def model(self):
        return ProjectWorks
