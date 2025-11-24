import logging
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import asc, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.sql import func

from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import (
    Leaves,
    Projects,
    ShiftReportDetails,
    ShiftReports,
    Users,
    WorkPrices,
)

logger = logging.getLogger("ok_service")


class ShiftManager(BaseDBManager):
    def _convert_to_uuid(self, value):
        """Приводит строку к UUID, если это ещё не UUID"""
        if isinstance(value, str):
            return UUID(value)
        return value

    def count_summ(self, work_id, shift_report_id, session=None):
        """Подсчитывает сумму работы с учётом сменных условий"""
        try:
            if session is None:
                with self.session_scope() as session:
                    return self._count_summ_internal(work_id, shift_report_id, session)
            else:
                return self._count_summ_internal(work_id, shift_report_id, session)
        except Exception as e:
            logger.error(f"Ошибка при подсчете суммы: {e}", extra={"login": "database"})
            raise

    def _count_summ_internal(self, work_id, shift_report_id, session):
        """Внутренний метод для подсчёта суммы, без открытия новой сессии"""

        shift_report_id = self._convert_to_uuid(shift_report_id)
        work_id = self._convert_to_uuid(work_id)

        shift_report = (
            session.query(ShiftReports)
            .filter(ShiftReports.shift_report_id == shift_report_id)
            .first()
        )

        user = session.query(Users).filter(Users.user_id == shift_report.user).first()

        if not shift_report:
            logger.warning(f"ShiftReport {shift_report_id} не найден")
            return Decimal(0)

        work_price = (
            session.query(WorkPrices)
            .filter(WorkPrices.work == work_id, WorkPrices.category == user.category)
            .first()
        )

        if not work_price:
            logger.warning(f"WorkPrices для work_id {work_id} не найден")
            return Decimal(0)

        price = work_price.price
        summ = price or Decimal(0)  # Берём цену работы

        if shift_report.extreme_conditions:
            logger.debug("Extreme conditions")
            summ += price * Decimal("0.25")

        if shift_report.night_shift:
            logger.debug("Night shift")
            summ += price * Decimal("0.25")

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
                .join(
                    ShiftReports,
                    ShiftReports.shift_report_id == ShiftReportDetails.shift_report,
                )
                .filter(ShiftReports.shift_report_id == shift_report_id)
                .scalar()
            )

            return result or 0  # Если записей нет, возвращаем 0

    def add_shift_report_with_details(self, data, created_by):
        """Добавляет shift_report и shift_report_details в одной транзакции"""

        shift_report_data = {
            "shift_report_id": uuid4(),
            "user": UUID(data["user"]),
            "date": data["date"],
            "date_start": data.get("date_start"),
            "date_end": data.get("date_end"),
            "project": UUID(data["project"]),
            "lng": data.get("lng"),
            "ltd": data.get("ltd"),
            "signed": data.get("signed", False),  # По умолчанию False
            "created_by": created_by,
            "extreme_conditions": data.get("extreme_conditions", False),
            "night_shift": data.get("night_shift", False),
        }

        shift_report_details_data = data.get(
            "details", []
        )  # Детали могут отсутствовать

        with self.session_scope() as session:
            try:
                leave_start = shift_report_data["date_start"] or shift_report_data["date"]
                leave_end = shift_report_data["date_end"] or shift_report_data["date"]
                leave_conflict = (
                    session.query(Leaves)
                    .filter(
                        Leaves.user_id == shift_report_data["user"],
                        Leaves.deleted.is_(False),
                        Leaves.start_date <= leave_end,
                        Leaves.end_date >= leave_start,
                    )
                    .first()
                )
                if leave_conflict:
                    raise ValueError("User has a leave during the requested date")

                # 1. Создаем `shift_report`
                new_report = ShiftReports(**shift_report_data)
                session.add(new_report)
                session.flush()  # Генерирует shift_report_id без коммита

                # 2. Создаем `shift_report_details`, если есть
                if shift_report_details_data:
                    details = [
                        ShiftReportDetails(
                            shift_report=new_report.shift_report_id,
                            work=UUID(detail["work"]),
                            quantity=detail["quantity"],
                            summ=(
                                self.count_summ(
                                    UUID(detail["work"]),
                                    new_report.shift_report_id,
                                    session,
                                )
                            )
                            * Decimal(detail["quantity"]),
                            created_by=created_by,
                            project_work=UUID(detail["project_work"]),
                        )
                        for detail in shift_report_details_data
                    ]

                    # Массовая вставка `shift_report_details`
                    session.add_all(details)

                session.commit()  # Сохраняем все одной транзакцией

                return new_report.to_dict()  # Возвращаем ID созданного отчета

            except SQLAlchemyError as e:
                session.rollback()
                raise e  # Выбрасываем исключение выше, чтобы обработать в API
            except ValueError:
                session.rollback()
                raise

    def get_project_leader(self, project):
        """Получение руководителя проекта по project"""
        try:
            logger.debug(
                f"Получение project_leader для project: {project}",
                extra={"login": "database"},
            )

            with self.session_scope() as session:
                shift_report = (
                    session.query(self.model)
                    .options(joinedload(self.model.projects))
                    .filter(self.model.project == project)
                    .first()
                )

                if not shift_report:
                    logger.warning(
                        f"ShiftReport с project {project} не найден",
                        extra={"login": "database"},
                    )
                    return None

                project_leader = shift_report.projects.project_leader
                if not project_leader:
                    logger.warning(
                        f"У проекта {project} нет руководителя",
                        extra={"login": "database"},
                    )
                    return None

                logger.info(
                    f"Найден project_leader {project_leader} для project {project}",
                    extra={"login": "database"},
                )
                return str(project_leader)

        except Exception as e:
            logger.error(
                f"Ошибка при получении project_leader: {e}", extra={"login": "database"}
            )
            raise

    def get_shift_reports_filtered(
        self, offset=0, limit=None, sort_by="created_at", sort_order="desc", **filters
    ):
        """Фильтрация отчетов по сменам с поддержкой диапазона дат и сортировки по user/project.name."""
        logger.debug(
            "get_shift_reports_filtered вызывается с фильтрацией, сортировкой и пагинацией.",
            extra={"login": "database"},
        )

        with self.session_scope() as session:
            query = session.query(self.model)

            # Aliases для join
            user_alias = aliased(Users)
            project_alias = aliased(Projects)

            # Фильтрация по дате
            if (
                filters.get("date_from")
                and filters.get("date_to")
                and hasattr(self.model, "date")
            ):
                column = getattr(self.model, "date")
                query = query.filter(
                    column.between(filters["date_from"], filters["date_to"])
                )
                logger.debug(
                    f"Фильтруем по дате: {filters['date_from']} - {filters['date_to']}",
                    extra={"login": "database"},
                )
            elif filters.get("date_from") and hasattr(self.model, "date"):
                query = query.filter(
                    getattr(self.model, "date") >= filters["date_from"]
                )
            elif filters.get("date_to") and hasattr(self.model, "date"):
                query = query.filter(getattr(self.model, "date") <= filters["date_to"])

            if (
                filters.get("date_start_from")
                and filters.get("date_start_to")
                and hasattr(self.model, "date_start")
            ):
                column = getattr(self.model, "date_start")
                query = query.filter(
                    column.between(filters["date_start_from"], filters["date_start_to"])
                )
            elif filters.get("date_start_from") and hasattr(self.model, "date_start"):
                query = query.filter(
                    getattr(self.model, "date_start") >= filters["date_start_from"]
                )
            elif filters.get("date_start_to") and hasattr(self.model, "date_start"):
                query = query.filter(
                    getattr(self.model, "date_start") <= filters["date_start_to"]
                )

            if (
                filters.get("date_end_from")
                and filters.get("date_end_to")
                and hasattr(self.model, "date_end")
            ):
                column = getattr(self.model, "date_end")
                query = query.filter(
                    column.between(filters["date_end_from"], filters["date_end_to"])
                )
            elif filters.get("date_end_from") and hasattr(self.model, "date_end"):
                query = query.filter(
                    getattr(self.model, "date_end") >= filters["date_end_from"]
                )
            elif filters.get("date_end_to") and hasattr(self.model, "date_end"):
                query = query.filter(
                    getattr(self.model, "date_end") <= filters["date_end_to"]
                )

            # Остальные фильтры
            for key, value in filters.items():
                if key in [
                    "date_from",
                    "date_to",
                    "date_start_from",
                    "date_start_to",
                    "date_end_from",
                    "date_end_to",
                ]:
                    continue
                if value is not None and hasattr(self.model, key):
                    column = getattr(self.model, key)
                    query = query.filter(
                        column.in_(value)
                        if isinstance(value, (list, tuple, set))
                        else column == value
                    )

            order = desc if sort_order == "desc" else asc
            if sort_by:
                if sort_by == "user":
                    query = query.join(user_alias, self.model.users)
                    query = query.order_by(order(user_alias.name))
                elif sort_by == "project":
                    query = query.join(project_alias, self.model.projects)
                    query = query.order_by(order(project_alias.name))
                elif hasattr(self.model, sort_by):
                    query = query.order_by(order(getattr(self.model, sort_by)))

            # Получение общего количества
            total_count = session.query(query.subquery()).count()
            logger.debug(
                f"Общее количество записей: {total_count}", extra={"login": "database"}
            )

            # Пагинация
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            records = query.all()
            logger.debug(
                f"Найдено записей (после пагинации): {len(records)}",
                extra={"login": "database"},
            )
            return total_count, [record.to_dict() for record in records]


class ShiftReportsDetailsManager(ShiftManager):
    @property
    def model(self):
        return ShiftReportDetails

    def add_shift_report_deatails(self, created_by, **data):
        try:
            with self.session_scope() as session:
                summ = self.count_summ(
                    UUID(data["work"]), UUID(data["shift_report"]), session
                )
                new_record = ShiftReportDetails(
                    shift_report=data["shift_report"],
                    work=data["work"],
                    quantity=data["quantity"],
                    summ=summ * Decimal(data["quantity"]),
                    created_by=created_by,
                    project_work=data["project_work"],
                )
                session.add(new_record)
                try:
                    session.flush()
                except Exception:
                    session.rollback()
                    raise
                return new_record.to_dict()
        except Exception as e:
            logger.error(
                f"""Ошибка при добавлении записи: {e}""", extra={"login": "database"}
            )
            raise

    def update_summ(
        self, work_id, quantity, extreme_conditions, night_shift, session, user_id
    ):
        """Пересчитывает сумму для конкретной работы"""
        logger.debug(
            f"[DEBUG] Входные данные: work_id={work_id}, quantity={quantity}, "
            f"extreme_conditions={extreme_conditions}, night_shift={night_shift}, user_id={user_id}"
        )

        # Преобразуем ID к UUID, если это строка
        user_id = self._convert_to_uuid(user_id)
        work_id = self._convert_to_uuid(work_id)

        logger.debug(
            f"[DEBUG] Преобразованные UUID: work_id={work_id}, user_id={user_id}"
        )

        # Получаем пользователя
        user = session.query(Users).filter(Users.user_id == user_id).first()

        if not user:
            logger.warning(f"[WARNING] Пользователь с ID {user_id} не найден!")
            return Decimal(0)

        logger.debug(
            f"[DEBUG] Найден пользователь: {user.user_id}, категория: {user.category}"
        )

        # Получаем цену работы
        work_price = (
            session.query(WorkPrices)
            .filter(WorkPrices.work == work_id, WorkPrices.category == user.category)
            .first()
        )

        if not work_price:
            logger.warning(
                f"[WARNING] Цена работы для work_id {work_id} и категории {user.category} не найдена!"
            )
            return Decimal(0)

        price = work_price.price
        logger.debug(f"[DEBUG] Найдена цена работы: {price}")

        # Инициализируем сумму
        summ = price or Decimal(0)
        logger.debug(f"[DEBUG] Базовая сумма: {summ}")

        # Применяем коэффициенты
        if extreme_conditions:
            logger.debug("[DEBUG] Extreme conditions применяются (увеличение на 25%)")
            summ += price * Decimal("0.25")

        if night_shift:
            logger.debug("[DEBUG] Night shift применяется (увеличение на 25%)")
            summ += price * Decimal("0.25")

        # Итоговая сумма
        total_summ = summ * Decimal(quantity)
        logger.debug(
            f"[DEBUG] Итоговая сумма (с учетом количества {quantity}): {total_summ}"
        )

        return total_summ

    def update_shift_report_details(self, shift_report_detail_id, **data):
        """Обновление записи по ID, игнорируя None в аргументах."""
        try:
            with self.session_scope() as session:
                logger.debug(
                    f"[DEBUG] Обновление shift_report_detail {shift_report_detail_id} с данными: {data}"
                )

                detail = (
                    session.query(ShiftReportDetails)
                    .filter(
                        ShiftReportDetails.shift_report_detail_id
                        == shift_report_detail_id
                    )
                    .first()
                )

                if not detail:
                    logger.warning(
                        f"[WARNING] Запись ShiftReportDetails с ID {shift_report_detail_id} не найдена!"
                    )
                    return None

                # Получаем shift_report
                shift_report = (
                    session.query(ShiftReports)
                    .filter(ShiftReports.shift_report_id == detail.shift_report)
                    .first()
                )

                if not shift_report:
                    logger.warning(
                        f"[WARNING] ShiftReport с ID {detail.shift_report} не найден!"
                    )
                    return None

                # Обновляем данные
                # Оставляем текущее значение, если work не передан
                detail.work = data.get("work", detail.work)
                detail.quantity = data.get("quantity", detail.quantity)
                detail.project_work = data.get("project_work", detail.project_work)

                # Пересчёт суммы
                detail.summ = self.update_summ(
                    detail.work,
                    detail.quantity,
                    shift_report.extreme_conditions,
                    shift_report.night_shift,
                    session,
                    shift_report.user,
                )

                session.commit()
                logger.info(
                    f"[INFO] Обновлены данные для shift_report_detail {shift_report_detail_id}"
                )

                return detail

        except Exception as e:
            logger.error(
                f"[ERROR] Ошибка при обновлении записи {shift_report_detail_id}: {e}",
                extra={"login": "database"},
            )
            raise

    def recalculate_by_conditions(
        self, shift_report_id, extreme_conditions, night_shift, user
    ):
        """Пересчитывает сумму (summ) для всех записей в ShiftReportDetails, если изменились условия"""

        shift_report_id = self._convert_to_uuid(shift_report_id)
        user = self._convert_to_uuid(user)

        with self.session_scope() as session:
            try:
                logger.debug(
                    f"[DEBUG] Начало пересчёта для shift_report_id={shift_report_id}, "
                    f"extreme_conditions={extreme_conditions}, night_shift={night_shift}, user={user}"
                )

                details = (
                    session.query(ShiftReportDetails)
                    .filter(ShiftReportDetails.shift_report == shift_report_id)
                    .all()
                )

                logger.debug(f"[DEBUG] Найдено {len(details)} записей для пересчёта")

                if not details:
                    logger.warning(
                        f"[WARNING] Нет записей в ShiftReportDetails для shift_report_id={shift_report_id}"
                    )
                    return

                for detail in details:
                    logger.debug(
                        f"[DEBUG] Пересчёт для detail_id={detail.shift_report_detail_id}, "
                        f"work={detail.work}, quantity={detail.quantity}"
                    )

                    new_summ = self.update_summ(
                        detail.work,
                        detail.quantity,
                        extreme_conditions,
                        night_shift,
                        session,
                        user,
                    )

                    logger.debug(
                        f"[DEBUG] Новая сумма: {new_summ} (было {detail.summ})"
                    )
                    detail.summ = new_summ  # Обновляем сумму

                session.commit()  # Фиксируем изменения
                logger.info(f"[INFO] Обновлены суммы для ShiftReport {shift_report_id}")

            except Exception as e:
                logger.error(
                    f"[ERROR] Ошибка при пересчете суммы для ShiftReport {shift_report_id}: {e}",
                    extra={"login": "database"},
                )
                raise
