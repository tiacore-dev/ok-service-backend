import logging
import uuid
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, asc, case, desc, func
from sqlalchemy.orm import joinedload

# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import (
    Objects,
    ProjectMaterials,
    Projects,
    ProjectSchedules,
    ProjectWorks,
    ShiftReportDetails,
    ShiftReportMaterials,
    ShiftReports,
    WorkMaterialRelations,
    Acceptances,
    WorkAcceptanceRelations,
)
from app.domain.projects import ProjectStatus, ProjectValidationError

logger = logging.getLogger("ok_service")

EXACT_MATCH_FIELDS = {"status"}


class ProjectsManager(BaseDBManager):
    @property
    def model(self):
        return Projects

    def get_all_filtered_with_status(
        self,
        user: dict[str, Any],
        offset: int = 0,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        **filters: Any,
    ):
        logger.debug(
            "get_all_filtered_with_status вызывается с фильтрацией, "
            "сортировкой и проверкой статуса объекта.",
            extra={"login": "database"},
        )

        with self.session_scope() as session:
            query = session.query(self.model).options(
                joinedload(Projects.objects)
            )  # Используем joinload для оптимизации

            # Если пользователь — обычный "user", фильтруем проекты по статусу объекта
            if user["role"] == "user":
                query = query.join(
                    Objects, Projects.object == Objects.object_id
                ).filter(Objects.status == "active")
                logger.debug(
                    "Фильтрация: только проекты с объектами в статусе 'active'.",
                    extra={"login": "database"},
                )
            # Применяем стандартные фильтры из filters
            filter_conditions = []
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    column = getattr(self.model, key)

                    # Проверяем, является ли значение UUID (обычно 36 символов)
                    if isinstance(value, uuid.UUID) or (
                        isinstance(value, str) and len(value) == 36 and "-" in value
                    ):
                        filter_conditions.append(column == value)
                        logger.debug(
                            f"Применяем точный UUID-фильтр: {key} = {value}",
                            extra={"login": "database"},
                        )

                    # Поля, требующие точного сравнения
                    elif key in EXACT_MATCH_FIELDS:
                        filter_conditions.append(column == value)
                        logger.debug(
                            f"Применяем точный фильтр для {key}: {key} = {value}",
                            extra={"login": "database"},
                        )

                    elif isinstance(value, str):
                        value = value.strip()  # Убираем лишние пробелы

                        if "%" not in value:
                            # Добавляем wildcard для частичного поиска
                            value = f"%{value}%"

                        filter_conditions.append(column.ilike(value))
                        logger.debug(
                            f"Применяем ILIKE-фильтр: {key} LIKE {value}",
                            extra={"login": "database"},
                        )

                    else:
                        filter_conditions.append(column == value)
                        logger.debug(
                            f"Применяем фильтр: {key} = {value}",
                            extra={"login": "database"},
                        )

            # Добавляем фильтры в запрос
            if filter_conditions:
                query = query.filter(and_(*filter_conditions))

            # Применяем сортировку
            if sort_by and hasattr(self.model, sort_by):
                order = desc if sort_order == "desc" else asc
                query = query.order_by(order(getattr(self.model, sort_by)))
                logger.debug(
                    f"Применяем сортировку: {sort_by} {sort_order}",
                    extra={"login": "database"},
                )

            # Применяем пагинацию
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            records = query.all()
            logger.debug(
                f"Найдено записей: {len(records)}", extra={"login": "database"}
            )

            return [record.to_dict() for record in records]

    def get_projects_by_leader(self, user_id):
        """Получает список проектов, где указанный пользователь является прорабом."""
        try:
            logger.debug(
                f"Fetching projects for project leader: {user_id}",
                extra={"login": "database"},
            )

            with self.session_scope() as session:
                projects = (
                    session.query(Projects)
                    .filter(Projects.project_leader == user_id)
                    .all()
                )

                result = [project.to_dict() for project in projects]

                logger.info(
                    f"Found {len(result)} projects for project leader {user_id}",
                    extra={"login": "database"},
                )

                return result

        except Exception as e:
            logger.error(
                f"Error fetching projects for leader {user_id}: {e}",
                extra={"login": "database"},
            )
            return []

    def get_project_stats(self, project_id):
        try:
            logger.debug(
                f"Fetching project for project id: {project_id}",
                extra={"login": "database"},
            )

            with self.session_scope() as session:
                plan_rows = (
                    session.query(
                        ProjectWorks.work,
                        func.sum(ProjectWorks.quantity),
                        func.sum(ProjectWorks.price * ProjectWorks.quantity),
                        func.max(ProjectWorks.project_work_name),
                    )
                    .filter(ProjectWorks.project == project_id)
                    .group_by(ProjectWorks.work)
                    .all()
                )
                result = {
                    str(work_id): {
                        "project_work_quantity": float(quantity or 0),
                        "project_work_summ": float(summ or 0),
                        "shift_report_details_quantity": 0.0,
                        "shift_report_details_summ": 0.0,
                        "shift_report_details_summ_by_estimate": 0.0,
                        "presented_quantity": None,
                        "presented_summ": None,
                        "accepted_quantity": None,
                        "accepted_summ": None,
                        "project_work_name": name,
                    }
                    for work_id, quantity, summ, name in plan_rows
                }
                actual_rows = (
                    session.query(
                        ShiftReportDetails.work,
                        func.sum(ShiftReportDetails.quantity),
                        func.sum(ShiftReportDetails.summ),
                        func.sum(ShiftReportDetails.quantity * ProjectWorks.price),
                    )
                    .join(
                        ShiftReports,
                        ShiftReports.shift_report_id == ShiftReportDetails.shift_report,
                    )
                    .outerjoin(
                        ProjectWorks,
                        ProjectWorks.project_work_id == ShiftReportDetails.project_work,
                    )
                    .filter(
                        ShiftReports.project == project_id,
                        ShiftReports.signed.is_(True),
                        ShiftReports.deleted.is_(False),
                    )
                    .group_by(ShiftReportDetails.work)
                    .all()
                )
                for work_id, quantity, summ, estimated_summ in actual_rows:
                    stats = result.get(str(work_id))
                    if stats is not None:
                        stats["shift_report_details_quantity"] = float(quantity or 0)
                        stats["shift_report_details_summ"] = float(summ or 0)
                        stats["shift_report_details_summ_by_estimate"] = float(
                            estimated_summ or 0
                        )

                project_work_prices = (
                    session.query(
                        ProjectWorks.project.label("project_id"),
                        ProjectWorks.work.label("work_id"),
                        (
                            func.sum(ProjectWorks.price * ProjectWorks.quantity)
                            / func.nullif(func.sum(ProjectWorks.quantity), 0)
                        ).label("price"),
                    )
                    .filter(ProjectWorks.project == project_id)
                    .group_by(ProjectWorks.project, ProjectWorks.work)
                    .subquery()
                )
                acceptance_rows = (
                    session.query(
                        WorkAcceptanceRelations.work_id,
                        func.sum(WorkAcceptanceRelations.quantity),
                        func.sum(
                            WorkAcceptanceRelations.quantity * project_work_prices.c.price
                        ),
                        func.sum(
                            case(
                                (
                                    Acceptances.status == "documents_signed",
                                    WorkAcceptanceRelations.quantity,
                                ),
                                else_=0,
                            )
                        ),
                        func.sum(
                            case(
                                (
                                    Acceptances.status == "documents_signed",
                                    WorkAcceptanceRelations.quantity * project_work_prices.c.price,
                                ),
                                else_=0,
                            )
                        ),
                    )
                    .join(
                        Acceptances,
                        Acceptances.id == WorkAcceptanceRelations.acceptance_id,
                    )
                    .outerjoin(
                        project_work_prices,
                        and_(
                            project_work_prices.c.project_id == Acceptances.project_id,
                            project_work_prices.c.work_id == WorkAcceptanceRelations.work_id,
                        ),
                    )
                    .filter(Acceptances.project_id == project_id)
                    .group_by(WorkAcceptanceRelations.work_id)
                    .all()
                )
                for work_id, presented_qty, presented_summ, accepted_qty, accepted_summ in acceptance_rows:
                    stats = result.get(str(work_id))
                    if stats is None:
                        continue
                    stats["presented_quantity"] = float(presented_qty) if presented_qty is not None else None
                    stats["presented_summ"] = float(presented_summ) if presented_summ is not None else None
                    stats["accepted_quantity"] = float(accepted_qty) if accepted_qty is not None else None
                    stats["accepted_summ"] = float(accepted_summ) if accepted_summ is not None else None
                return result
        except Exception as e:
            logger.error(
                f"Error fetching projects for leader {project_id}: {e}",
                extra={"login": "database"},
            )
            return {}

    def get_project_stats_many(self, project_ids):
        """Load plan, shift and acceptance aggregates for all projects in a batch."""
        project_ids = list(project_ids)
        if not project_ids:
            return {}
        try:
            with self.session_scope() as session:
                stats_by_project = {project_id: {} for project_id in project_ids}
                plan_rows = (
                    session.query(
                        ProjectWorks.project,
                        ProjectWorks.work,
                        func.sum(ProjectWorks.quantity),
                        func.sum(ProjectWorks.price * ProjectWorks.quantity),
                        func.max(ProjectWorks.project_work_name),
                    )
                    .filter(ProjectWorks.project.in_(project_ids))
                    .group_by(ProjectWorks.project, ProjectWorks.work)
                    .all()
                )
                for project_id, work_id, quantity, summ, name in plan_rows:
                    stats_by_project[project_id][str(work_id)] = {
                        "project_work_quantity": float(quantity or 0),
                        "project_work_summ": float(summ or 0),
                        "shift_report_details_quantity": 0.0,
                        "shift_report_details_summ": 0.0,
                        "shift_report_details_summ_by_estimate": 0.0,
                        "presented_quantity": None,
                        "presented_summ": None,
                        "accepted_quantity": None,
                        "accepted_summ": None,
                        "project_work_name": name,
                    }

                actual_rows = (
                    session.query(
                        ShiftReports.project,
                        ShiftReportDetails.work,
                        func.sum(ShiftReportDetails.quantity),
                        func.sum(ShiftReportDetails.summ),
                        func.sum(ShiftReportDetails.quantity * ProjectWorks.price),
                    )
                    .join(
                        ShiftReports,
                        ShiftReports.shift_report_id == ShiftReportDetails.shift_report,
                    )
                    .outerjoin(
                        ProjectWorks,
                        ProjectWorks.project_work_id == ShiftReportDetails.project_work,
                    )
                    .filter(
                        ShiftReports.project.in_(project_ids),
                        ShiftReports.signed.is_(True),
                        ShiftReports.deleted.is_(False),
                    )
                    .group_by(ShiftReports.project, ShiftReportDetails.work)
                    .all()
                )
                for project_id, work_id, quantity, summ, estimated_summ in actual_rows:
                    stats = stats_by_project[project_id].get(str(work_id))
                    if stats is not None:
                        stats["shift_report_details_quantity"] = float(quantity or 0)
                        stats["shift_report_details_summ"] = float(summ or 0)
                        stats["shift_report_details_summ_by_estimate"] = float(
                            estimated_summ or 0
                        )

                project_work_prices = (
                    session.query(
                        ProjectWorks.project.label("project_id"),
                        ProjectWorks.work.label("work_id"),
                        (
                            func.sum(ProjectWorks.price * ProjectWorks.quantity)
                            / func.nullif(func.sum(ProjectWorks.quantity), 0)
                        ).label("price"),
                    )
                    .filter(ProjectWorks.project.in_(project_ids))
                    .group_by(ProjectWorks.project, ProjectWorks.work)
                    .subquery()
                )
                acceptance_rows = (
                    session.query(
                        Acceptances.project_id,
                        WorkAcceptanceRelations.work_id,
                        func.sum(WorkAcceptanceRelations.quantity),
                        func.sum(
                            WorkAcceptanceRelations.quantity * project_work_prices.c.price
                        ),
                        func.sum(
                            case(
                                (
                                    Acceptances.status == "documents_signed",
                                    WorkAcceptanceRelations.quantity,
                                ),
                                else_=0,
                            )
                        ),
                        func.sum(
                            case(
                                (
                                    Acceptances.status == "documents_signed",
                                    WorkAcceptanceRelations.quantity * project_work_prices.c.price,
                                ),
                                else_=0,
                            )
                        ),
                    )
                    .join(
                        Acceptances,
                        Acceptances.id == WorkAcceptanceRelations.acceptance_id,
                    )
                    .outerjoin(
                        project_work_prices,
                        and_(
                            project_work_prices.c.project_id == Acceptances.project_id,
                            project_work_prices.c.work_id == WorkAcceptanceRelations.work_id,
                        ),
                    )
                    .filter(Acceptances.project_id.in_(project_ids))
                    .group_by(Acceptances.project_id, WorkAcceptanceRelations.work_id)
                    .all()
                )
                for project_id, work_id, presented_qty, presented_summ, accepted_qty, accepted_summ in acceptance_rows:
                    stats = stats_by_project[project_id].get(str(work_id))
                    if stats is not None:
                        stats["presented_quantity"] = float(presented_qty) if presented_qty is not None else None
                        stats["presented_summ"] = float(presented_summ) if presented_summ is not None else None
                        stats["accepted_quantity"] = float(accepted_qty) if accepted_qty is not None else None
                        stats["accepted_summ"] = float(accepted_summ) if accepted_summ is not None else None
                return stats_by_project
        except Exception as error:
            logger.error("Error fetching batched project statistics: %s", error)
            return {project_id: {} for project_id in project_ids}

    def get_object_stats(self, object_id):
        with self.session_scope() as session:
            projects = (
                session.query(Projects.project_id, Projects.name)
                .filter(
                    Projects.object == object_id,
                    Projects.deleted.is_(False),
                )
                .order_by(Projects.created_at.asc())
                .all()
            )

        return self._build_grouped_project_stats(projects, detailed=False)

    def get_object_stats_details(self, object_id):
        with self.session_scope() as session:
            projects = (
                session.query(Projects.project_id, Projects.name)
                .filter(
                    Projects.object == object_id,
                    Projects.deleted.is_(False),
                )
                .order_by(Projects.created_at.asc())
                .all()
            )

        return self._build_grouped_project_stats(projects, detailed=True)

    def get_project_leader_stats(self, project_leader_id):
        with self.session_scope() as session:
            projects = (
                session.query(Projects.project_id, Projects.name)
                .filter(
                    Projects.project_leader == project_leader_id,
                    Projects.deleted.is_(False),
                )
                .order_by(Projects.created_at.asc())
                .all()
            )
        return self._build_grouped_project_stats(projects, detailed=False)

    def get_project_leader_stats_details(self, project_leader_id):
        with self.session_scope() as session:
            projects = (
                session.query(Projects.project_id, Projects.name)
                .filter(
                    Projects.project_leader == project_leader_id,
                    Projects.deleted.is_(False),
                )
                .order_by(Projects.created_at.asc())
                .all()
            )
        return self._build_grouped_project_stats(projects, detailed=True)

    def _build_grouped_project_stats(self, projects, *, detailed):
        if not projects:
            return {"total": {}, "projects": []}
        project_stats = []
        total = {}
        if not detailed:
            total = {field: None for field in self._stat_summary_fields()}
        stats_by_project = self.get_project_stats_many(
            [project_id for project_id, _ in projects]
        )
        for project_id, name in projects:
            stats = stats_by_project.get(project_id, {})
            value = stats if detailed else self._summarize_project_stats(stats)
            project_stats.append(
                {"project_id": str(project_id), "name": name, "stats": value}
            )
            if detailed:
                self._merge_detailed_stats(total, stats)
            else:
                self._merge_stats_summary(total, value)
        return {"total": total, "projects": project_stats}

    @staticmethod
    def _merge_detailed_stats(total, stats):
        for work_id, work_stats in stats.items():
            if work_id not in total:
                total[work_id] = dict(work_stats)
                continue
            for field, value in work_stats.items():
                if isinstance(value, (int, float)):
                    total[work_id][field] = (total[work_id].get(field) or 0) + value
                elif total[work_id].get(field) is None and value is not None:
                    total[work_id][field] = value

    @staticmethod
    def _stat_summary_fields():
        return (
            "project_work_quantity",
            "project_work_summ",
            "shift_report_details_quantity",
            "shift_report_details_summ",
            "shift_report_details_summ_by_estimate",
            "presented_quantity",
            "presented_summ",
            "accepted_quantity",
            "accepted_summ",
        )

    @classmethod
    def _summarize_project_stats(cls, stats):
        fields = cls._stat_summary_fields()
        summary = {field: None for field in fields}
        for item in stats.values():
            for field in fields:
                value = item.get(field)
                if value is not None:
                    summary[field] = (summary[field] or 0) + value
        return summary

    @staticmethod
    def _merge_stats_summary(total, summary):
        for field, value in summary.items():
            if value is not None:
                total[field] = (total.get(field) or 0) + value

    def get_all_project_ids(self) -> list[UUID]:
        with self.session_scope() as session:
            return [project_id for (project_id,) in session.query(Projects.project_id)]

    def get_project_statuses_by_object(self, object_id: UUID) -> list[str]:
        with self.session_scope() as session:
            return [
                status.value if hasattr(status, "value") else str(status)
                for (status,) in session.query(Projects.status)
                .filter(Projects.object == object_id, Projects.deleted.is_(False))
                .all()
            ]

    def update_status_if_current(
        self,
        project_id: UUID,
        expected_status: ProjectStatus,
        new_status: ProjectStatus,
    ) -> dict[str, Any] | None:
        with self.session_scope() as session:
            project = (
                session.query(Projects)
                .filter(
                    Projects.project_id == project_id,
                    Projects.status == expected_status,
                )
                .with_for_update()
                .first()
            )
            if project is None:
                return None
            if new_status is ProjectStatus.CLOSED:
                project_works = (
                    session.query(ProjectWorks)
                    .filter(ProjectWorks.project == project_id)
                    .with_for_update()
                    .all()
                )
                if any(not project_work.signed for project_work in project_works):
                    raise ProjectValidationError(
                        "Project cannot be closed until all project works are signed"
                    )
            project.status = new_status
            session.flush()
            return project.to_dict()

    def get_project_stats_by_project_work(self, project_id):
        try:
            logger.debug(
                f"Fetching project stats BY PROJECT WORK for project id: {project_id}",
                extra={"login": "database"},
            )

            with self.session_scope() as session:
                project_works = (
                    session.query(ProjectWorks)
                    .filter(ProjectWorks.project == project_id)
                    .all()
                )

                result = {
                    str(work.project_work_id): {
                        "project_work_quantity": 0,
                        "shift_report_details_quantity": 0,
                        "project_work_name": work.project_work_name,
                    }
                    for work in project_works
                }

                project_works = [work.to_dict() for work in project_works]
                for work in project_works:
                    work_id = str(work["project_work_id"])
                    if isinstance(work["quantity"], Decimal):
                        work["quantity"] = float(work["quantity"])
                    result[work_id]["project_work_quantity"] += work["quantity"]

                reports = (
                    session.query(ShiftReports)
                    .filter(
                        ShiftReports.project == project_id,
                        ShiftReports.signed.is_(True),
                    )
                    .all()
                )

                reports = [report.to_dict() for report in reports]
                for report in reports:
                    details = (
                        session.query(ShiftReportDetails)
                        .filter(
                            ShiftReportDetails.shift_report
                            == UUID(report["shift_report_id"])
                        )
                        .all()
                    )
                    details = [detail.to_dict() for detail in details]

                    for detail in details:
                        project_work = detail.get("project_work") or {}
                        detail_project_work_id = project_work.get("project_work_id")
                        if not detail_project_work_id:
                            continue
                        detail_project_work_id = str(detail_project_work_id)
                        if isinstance(detail["quantity"], Decimal):
                            detail["quantity"] = float(detail["quantity"])
                        if detail_project_work_id in result:
                            result[detail_project_work_id][
                                "shift_report_details_quantity"
                            ] += detail["quantity"]
                        else:
                            logger.warning(
                                f"Work ID {detail_project_work_id} not found in result",
                                extra={"login": "database"},
                            )

                return result
        except Exception as e:
            logger.error(
                f"Error fetching project stats by project_work for project {
                    project_id
                }: {e}",
                extra={"login": "database"},
            )
            return {}

    def get_project_stats_by_project_materials(self, project_id):
        try:
            logger.debug(
                f"Fetching project stats BY PROJECT MATERIALS for project id: {
                    project_id
                }",
                extra={"login": "database"},
            )

            with self.session_scope() as session:
                project_materials = (
                    session.query(ProjectMaterials)
                    .filter(ProjectMaterials.project == project_id)
                    .all()
                )

                result = {
                    str(pm.material): {
                        "project_material_quantity": 0,
                        "shift_report_materials_quantity": 0,
                        "material_name": pm.materials.name if pm.materials else None,
                    }
                    for pm in project_materials
                }

                for pm in project_materials:
                    material_id = str(pm.material)
                    quantity = pm.quantity
                    if isinstance(quantity, Decimal):
                        quantity = float(quantity)
                    if material_id not in result:
                        result[material_id] = {
                            "project_material_quantity": 0,
                            "shift_report_materials_quantity": 0,
                            "material_name": pm.materials.name
                            if pm.materials
                            else None,
                        }
                    result[material_id]["project_material_quantity"] += quantity

                reports = (
                    session.query(ShiftReports)
                    .filter(
                        ShiftReports.project == project_id,
                        ShiftReports.signed.is_(True),
                    )
                    .all()
                )

                report_ids = [report.shift_report_id for report in reports]
                if report_ids:
                    shift_materials = (
                        session.query(ShiftReportMaterials)
                        .filter(ShiftReportMaterials.shift_report.in_(report_ids))
                        .all()
                    )
                else:
                    shift_materials = []

                for sm in shift_materials:
                    material_id = str(sm.material)
                    quantity = sm.quantity
                    if isinstance(quantity, Decimal):
                        quantity = float(quantity)

                    if material_id not in result:
                        result[material_id] = {
                            "project_material_quantity": 0,
                            "shift_report_materials_quantity": 0,
                            "material_name": None,
                        }
                    result[material_id]["shift_report_materials_quantity"] += quantity

                return result
        except Exception as e:
            logger.error(
                f"Error fetching project stats by project materials for project {
                    project_id
                }: {e}",
                extra={"login": "database"},
            )
            return {}


class ProjectSchedulesManager(BaseDBManager):
    @property
    def model(self):
        return ProjectSchedules

    def get_schedule_ids_by_project_leader(self, user_id):
        """
        Возвращает ID всех ProjectWorks, где пользователь является project_leader.
        """
        leader_id = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        with self.session_scope() as session:
            schedule_ids = (
                session.query(ProjectSchedules.project_schedule_id)
                .join(Projects, ProjectSchedules.project == Projects.project_id)
                .filter(Projects.project_leader == leader_id)
                .all()
            )

            # ✅ Достаём первый элемент из tuple
            result = [str(schedule_id[0]) for schedule_id in schedule_ids]
            logger.debug(
                f"Найдено {len(result)} работ для project_leader={user_id}",
                extra={"login": "database"},
            )
            return result


class ProjectWorksManager(BaseDBManager):
    @property
    def model(self):
        return ProjectWorks

    def _sync_project_materials(self, session, project_work, created_by):
        session.query(ProjectMaterials).filter(
            ProjectMaterials.project_work == project_work.project_work_id
        ).delete(synchronize_session=False)

        relations = (
            session.query(WorkMaterialRelations)
            .options(joinedload(WorkMaterialRelations.materials))
            .filter(WorkMaterialRelations.work == project_work.work)
            .all()
        )
        if not relations:
            return

        for relation in relations:
            quantity = Decimal(project_work.quantity) * Decimal(relation.quantity)
            material = relation.materials
            if material and material.measurement_unit:
                unit = str(material.measurement_unit_ref.name).strip().lower()
                if unit == "шт.":
                    quantity = Decimal(int(quantity))

            session.add(
                ProjectMaterials(
                    project_material_id=uuid.uuid4(),
                    project=project_work.project,
                    material=relation.material,
                    quantity=quantity,
                    project_work=project_work.project_work_id,
                    created_by=created_by,
                )
            )

    def add(self, **kwargs):
        created_by = kwargs.get("created_by")
        with self.session_scope() as session:
            new_record = self.model(**kwargs)  # type: ignore
            session.add(new_record)
            session.flush()
            self._sync_project_materials(
                session, new_record, created_by or new_record.created_by
            )
            return new_record.to_dict()

    def update(self, record_id, **kwargs):
        filtered_kwargs = {
            key: value for key, value in kwargs.items() if value is not None
        }
        if not filtered_kwargs:
            return None

        with self.session_scope() as session:
            record = (
                session.query(self.model)
                .filter(self.model.project_work_id == record_id)
                .first()
            )
            if not record:
                return None

            for key, value in filtered_kwargs.items():
                setattr(record, key, value)

            session.flush()
            self._sync_project_materials(session, record, record.created_by)
            return record.to_dict()

    def delete(self, record_id):
        with self.session_scope() as session:
            record = (
                session.query(self.model)
                .filter(self.model.project_work_id == record_id)
                .first()
            )
            if not record:
                return None

            session.query(ProjectMaterials).filter(
                ProjectMaterials.project_work == record.project_work_id
            ).delete(synchronize_session=False)
            session.delete(record)
            session.flush()
            return record.to_dict()

    def get_work_ids_by_project_leader(self, user_id):
        """
        Возвращает ID всех ProjectWorks, где пользователь является project_leader.
        """
        leader_id = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        with self.session_scope() as session:
            work_ids = (
                session.query(ProjectWorks.project_work_id)
                .join(Projects, ProjectWorks.project == Projects.project_id)
                .filter(Projects.project_leader == leader_id)
                .all()
            )

            # ✅ Достаём первый элемент из tuple
            result = [str(work_id[0]) for work_id in work_ids]
            logger.debug(
                f"Найдено {len(result)} работ для project_leader={user_id}",
                extra={"login": "database"},
            )
            return result

    def get_manager(self, project):
        """Получение ID менеджера объекта по project"""
        try:
            logger.debug(
                f"Получение manager ID для project: {project}",
                extra={"login": "database"},
            )

            with self.session_scope() as session:
                # 🔥 Загружаем Projects и Objects через Projects
                project_data = (
                    session.query(Projects)
                    .options(
                        # Теперь objects загружается через Projects
                        joinedload(Projects.objects)
                    )
                    .filter(Projects.project_id == project)
                    .first()
                )

                if not project_data or not project_data.objects:
                    logger.warning(
                        f"Проект {project} или его объект не найден",
                        extra={"login": "database"},
                    )
                    return None

                manager_id = project_data.objects.manager  # 🔥 Теперь это корректно
                if not manager_id:
                    logger.warning(
                        f"У объекта проекта {project} нет менеджера",
                        extra={"login": "database"},
                    )
                    return None

                logger.info(
                    f"Найден manager ID {manager_id} для project {project}",
                    extra={"login": "database"},
                )
                return str(manager_id)  # Приводим UUID к строке

        except Exception as e:
            logger.error(
                f"Ошибка при получении manager ID: {e}", extra={"login": "database"}
            )
            raise

    def get_project_leader(self, project_work_id):
        """Получение ID руководителя проекта по project_work_id"""
        try:
            logger.debug(
                f"Получение project_leader ID для project_work_id: {project_work_id}",
                extra={"login": "database"},
            )

            with self.session_scope() as session:
                project_work = (
                    session.query(self.model)
                    .options(joinedload(self.model.projects))
                    .filter(self.model.project_work_id == project_work_id)
                    .first()
                )

                if not project_work or not project_work.projects:
                    logger.warning(
                        f"ProjectWork с ID {project_work_id} или его проект не найден",
                        extra={"login": "database"},
                    )
                    return None

                project_leader = project_work.projects.project_leader
                if not project_leader:
                    logger.warning(
                        f"У проекта ProjectWork {project_work_id} нет руководителя",
                        extra={"login": "database"},
                    )
                    return None

                logger.info(
                    f"Найден project_leader ID {project_leader} для project_work_id {
                        project_work_id
                    }",
                    extra={"login": "database"},
                )
                return str(project_leader)  # Приводим UUID к строке

        except Exception as e:
            logger.error(
                f"Ошибка при получении project_leader ID: {e}",
                extra={"login": "database"},
            )
            raise
