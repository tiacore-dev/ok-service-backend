from uuid import uuid4, UUID
from decimal import Decimal
import logging
from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload
from sqlalchemy import asc, desc
from sqlalchemy.exc import SQLAlchemyError
from app.database.models import ShiftReports, ShiftReportDetails, WorkPrices
from app.database.managers.abstract_manager import BaseDBManager


logger = logging.getLogger('ok_service')


class ShiftManager(BaseDBManager):
    def count_summ(self, work_id, shift_report_id, session=None):
        """Подсчитывает сумму работы с учётом сменных условий"""
        try:
            if session is None:
                with self.session_scope() as session:
                    return self._count_summ_internal(work_id, shift_report_id, session)
            else:
                return self._count_summ_internal(work_id, shift_report_id, session)
        except Exception as e:
            logger.error(f"Ошибка при подсчете суммы: {e}", extra={
                         "login": "database"})
            raise

    def _count_summ_internal(self, work_id, shift_report_id, session):
        """Внутренний метод для подсчёта суммы, без открытия новой сессии"""
        shift_report = session.query(ShiftReports).filter(
            ShiftReports.shift_report_id == shift_report_id
        ).first()

        if not shift_report:
            logger.warning(f"ShiftReport {shift_report_id} не найден")
            return Decimal(0)

        work_price = session.query(WorkPrices).filter(
            WorkPrices.work == work_id
        ).first()

        if not work_price:
            logger.warning(f"WorkPrices для work_id {work_id} не найден")
            return Decimal(0)

        summ = work_price.price or Decimal(0)  # Берём цену работы

        logger.debug(
            f"Тип work_price.price: {type(work_price.price)}")  # Отладка
        logger.debug(
            f"Тип Decimal('0.25'): {type(Decimal('0.25'))}")  # Отладка

        if shift_report.extreme_conditions:
            summ *= Decimal("1.25")  # Увеличиваем на 25%

        if shift_report.night_shift:
            summ *= Decimal("1.25")  # Увеличиваем ещё на 25%

        return summ


class ShiftReportsManager(ShiftManager):

    @property
    def model(self):
        return ShiftReports

    def get_total_sum_by_shift_report(self, shift_report_id):
        """Возвращает сумму всех `summ` из shift_report_details для shift_report_id"""
        with self.session_scope() as session:
            result = (
                session.query(func.sum(ShiftReportDetails.summ))
                .join(ShiftReports, ShiftReports.shift_report_id == ShiftReportDetails.shift_report)
                .filter(ShiftReports.shift_report_id == shift_report_id)
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
                            summ=(self.count_summ(
                                UUID(detail['work']), new_report.shift_report_id, session))*Decimal(detail['quantity']),
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


class ShiftReportsDetailsManager(ShiftManager):

    @property
    def model(self):
        return ShiftReportDetails

    def add_shift_report_deatails(self, created_by, **data):
        try:
            with self.session_scope() as session:
                summ = self.count_summ(
                    UUID(data['work']), UUID(data['shift_report']), session)
                new_record = ShiftReportDetails(
                    shift_report=data['shift_report'],
                    work=data['work'],
                    quantity=data['quantity'],
                    summ=summ*Decimal(data['quantity']),
                    created_by=created_by
                )
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

    def recalculate_shift_details(self, shift_report_id):
        """Пересчитывает сумму (summ) для всех записей в ShiftReportDetails, если изменились условия"""
        with self.session_scope() as session:
            try:
                session.expire_all()  # Принудительно обновляем объекты перед запросом

                logger.debug(
                    f"[DEBUG] Получение деталей смены для {shift_report_id}")
                details = session.query(ShiftReportDetails).filter(
                    ShiftReportDetails.shift_report == shift_report_id
                ).all()
                logger.debug(f"[DEBUG] Найдено {len(details)} записей")

                if not details:
                    return

                for detail in details:
                    new_summ = self.count_summ(
                        detail.work, shift_report_id, session) * Decimal(detail.quantity)
                    detail.summ = new_summ  # Обновляем сумму

                session.commit()  # Фиксируем изменения
                logger.info(
                    f"Обновлены суммы для ShiftReport {shift_report_id}")
            except Exception as e:
                logger.error(f"""Ошибка при пересчете суммы: {
                    e}""", extra={"login": "database"})
                raise
