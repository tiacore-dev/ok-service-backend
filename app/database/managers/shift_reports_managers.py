from uuid import uuid4, UUID
import logging
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload
from sqlalchemy import asc, desc
from sqlalchemy.exc import SQLAlchemyError
from app.database.models import ShiftReports, ShiftReportDetails
from app.database.managers.abstract_manager import BaseDBManager


logger = logging.getLogger('ok_service')


class ShiftReportsManager(BaseDBManager):

    @property
    def model(self):
        return ShiftReports

    def get_total_sum_by_shift_report(self, shift_report_id):
        """Возвращает сумму всех `summ` из shift_report_details для shift_report_id"""
        with self.session_scope() as session:

            # Создаем алиасы для удобства
            sr = aliased(ShiftReports)
            srd = aliased(ShiftReportDetails)

            result = (
                session.query(func.sum(srd.summ))
                .select_from(sr)  # Явно указываем, с какой таблицы начинаем
                # Указываем ON-условие
                .join(srd, sr.shift_report_id == srd.shift_report)
                .filter(sr.shift_report_id == shift_report_id)
                .scalar()
            )

            return result or 0  # Если записей нет, возвращаем 0

    def add_shift_report_with_details(self, data, created_by):
        """Добавляет shift_report и shift_report_details в одной транзакции"""

        shift_report_data = {
            "shift_report_id": uuid4(),
            "user": UUID(data['user']),
            "date": data['date'],
            "project": UUID(data['project']),
            "signed": data.get("signed", False),  # По умолчанию False
            "created_by": created_by,
            "extreme_conditions": data.get('extreme_conditions', False),
            "night_shift": data.get('night_shift', False)
        }

        shift_report_details_data = data.get(
            "details", [])  # Детали могут отсутствовать

        with self.session_scope() as session:
            try:
                # 1. Создаем `shift_report`
                new_report = ShiftReports(**shift_report_data)
                session.add(new_report)
                session.flush()  # Генерирует shift_report_id без коммита

                # 2. Создаем `shift_report_details`, если есть
                if shift_report_details_data:
                    details = [
                        ShiftReportDetails(
                            shift_report=new_report.shift_report_id,
                            work=UUID(detail['work']),
                            quantity=detail['quantity'],
                            summ=detail['summ'],
                            created_by=created_by
                        ) for detail in shift_report_details_data
                    ]

                    # Массовая вставка `shift_report_details`
                    session.add_all(details)

                session.commit()  # Сохраняем все одной транзакцией

                return new_report.to_dict()  # Возвращаем ID созданного отчета

            except SQLAlchemyError as e:
                session.rollback()
                raise e  # Выбрасываем исключение выше, чтобы обработать в API

    def get_project_leader(self, project):
        """Получение руководителя проекта по project"""
        try:
            logger.debug(f"Получение project_leader для project: {project}", extra={
                         "login": "database"})

            with self.session_scope() as session:
                shift_report = session.query(self.model).options(
                    joinedload(self.model.projects)
                ).filter(self.model.project == project).first()

                if not shift_report:
                    logger.warning(f"ShiftReport с project {project} не найден", extra={
                                   "login": "database"})
                    return None

                project_leader = shift_report.projects.project_leader
                if not project_leader:
                    logger.warning(f"У проекта {project} нет руководителя", extra={
                                   "login": "database"})
                    return None

                logger.info(f"Найден project_leader {project_leader} для project {project}", extra={
                            "login": "database"})
                return str(project_leader)

        except Exception as e:
            logger.error(f"Ошибка при получении project_leader: {e}", extra={
                         "login": "database"})
            raise

    def get_shift_reports_filtered(self, offset=0, limit=None, sort_by="created_at", sort_order='desc', **filters):
        """Фильтрация отчетов по сменам с поддержкой диапазона дат."""
        logger.debug("get_shift_reports_filtered вызывается с фильтрацией, сортировкой и пагинацией.",
                     extra={"login": "database"})

        with self.session_scope() as session:
            query = session.query(self.model)

            # Фильтрация по остальным полям
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    column = getattr(self.model, key)

                    # Фильтрация по диапазону дат (если указаны обе границы)
                    if key == "date_from" and filters.get("date_to"):
                        query = query.filter(column.between(
                            filters["date_from"], filters["date_to"]))
                        logger.debug(f"Фильтруем по дате: {filters['date_from']} - {filters['date_to']}",
                                     extra={"login": "database"})

                    # Если указана только начальная дата (>=)
                    elif key == "date_from":
                        query = query.filter(column >= value)
                        logger.debug(f"Фильтруем по дате от: {value}",
                                     extra={"login": "database"})

                    # Если указана только конечная дата (<=)
                    elif key == "date_to":
                        query = query.filter(column <= value)
                        logger.debug(f"Фильтруем по дате до: {value}",
                                     extra={"login": "database"})

                    # Обычные точные фильтры
                    else:
                        query = query.filter(column == value)
                        logger.debug(f"Применяем фильтр: {key} = {value}",
                                     extra={"login": "database"})

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


class ShiftReportsDetailsManager(BaseDBManager):

    @property
    def model(self):
        return ShiftReportDetails
