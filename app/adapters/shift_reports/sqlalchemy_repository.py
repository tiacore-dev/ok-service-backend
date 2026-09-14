from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.adapters.statistics import ProjectWorkStatistics
from app.database.managers.projects_managers import ProjectsManager
from app.database.managers.shift_reports_managers import (
    ShiftReportsDetailsManager,
    ShiftReportsManager,
)
from app.domain.shift_reports import ShiftReport, ShiftReportDetail
from app.use_cases.shift_reports.dto import (
    CreateShiftReportCommand,
    CreateShiftReportDetailPayload,
    UpdateShiftReportCommand,
    UpdateShiftReportDetailCommand,
)
from app.use_cases.shift_reports.ports import ShiftReportRepository

from .mappers import (
    shift_report_detail_dict_to_entity,
    shift_report_dict_to_entity,
)


@dataclass(slots=True)
class SQLAlchemyShiftReportRepository(ShiftReportRepository):
    reports_manager: ShiftReportsManager = field(default_factory=ShiftReportsManager)
    details_manager: ShiftReportsDetailsManager = field(
        default_factory=ShiftReportsDetailsManager
    )
    projects_manager: ProjectsManager = field(default_factory=ProjectsManager)
    statistics: ProjectWorkStatistics | None = None

    def _recalculate(self, *project_ids: UUID | None) -> None:
        if self.statistics is not None:
            self.statistics.recalculate_many(
                {project_id for project_id in project_ids if project_id is not None}
            )

    def create_shift_report(self, command: CreateShiftReportCommand) -> ShiftReport:
        payload = {
            "user": command.user,
            "date": command.date,
            "date_start": command.date_start,
            "date_end": command.date_end,
            "project": command.project,
            "lng_start": command.lng_start,
            "ltd_start": command.ltd_start,
            "lng_end": command.lng_end,
            "ltd_end": command.ltd_end,
            "distance_start": command.distance_start,
            "distance_end": command.distance_end,
            "signed": command.signed,
            "night_shift": command.night_shift,
            "extreme_conditions": command.extreme_conditions,
            "comment": command.comment,
            "details": [
                {
                    "project_work": item.project_work,
                    "work": item.work,
                    "quantity": item.quantity,
                }
                for item in (command.details or [])
            ],
        }
        created = self.reports_manager.add_shift_report_with_details(
            payload, created_by=command.created_by or command.user
        )
        record = normalize_result(created)
        if record is None:
            raise ValueError("Shift report creation did not return a record")
        entity = shift_report_dict_to_entity(record)
        self._recalculate(entity.project)
        return entity

    def get_shift_report(self, shift_report_id: UUID) -> ShiftReport | None:
        record = normalize_result(self.reports_manager.get_by_id(shift_report_id))
        if record is None:
            return None
        return shift_report_dict_to_entity(record)

    def update_shift_report(
        self, command: UpdateShiftReportCommand
    ) -> ShiftReport | None:
        current = self.get_shift_report(command.shift_report_id)
        updated = self.reports_manager.update_shift_report(
            command.shift_report_id,
            user=command.user,
            date=command.date,
            date_start=command.date_start,
            date_end=command.date_end,
            project=command.project,
            lng_start=command.lng_start,
            ltd_start=command.ltd_start,
            lng_end=command.lng_end,
            ltd_end=command.ltd_end,
            distance_start=command.distance_start,
            distance_end=command.distance_end,
            signed=command.signed,
            night_shift=command.night_shift,
            extreme_conditions=command.extreme_conditions,
            deleted=command.deleted,
            comment=command.comment,
            updated_by=command.updated_by,
            leave_check_date=command.leave_check_date,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        entity = shift_report_dict_to_entity(record)
        self._recalculate(current.project if current else None, entity.project)
        return entity

    def sign_shift_report(
        self, shift_report_id: UUID, signed_by: UUID
    ) -> ShiftReport | None:
        record = normalize_result(
            self.reports_manager.sign_shift_report(shift_report_id, signed_by)
        )
        if record is None:
            return None
        entity = shift_report_dict_to_entity(record)
        self._recalculate(entity.project)
        return entity

    def delete_shift_report(self, shift_report_id: UUID) -> bool:
        current = self.get_shift_report(shift_report_id)
        deleted = self.reports_manager.delete(shift_report_id)
        if deleted is not None:
            self._recalculate(current.project if current else None)
        return deleted is not None

    def list_shift_reports(self, **filters) -> tuple[int, list[ShiftReport]]:
        total, records = self.reports_manager.get_shift_reports_filtered(**filters)
        return total, [shift_report_dict_to_entity(item) for item in records]

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]:
        projects = self.reports_manager.get_project_ids_by_leader(user_id)
        return [UUID(str(project)) for project in projects]

    def get_total_sum_by_shift_report(self, shift_report_id: UUID) -> int | float:
        return self.reports_manager.get_total_sum_by_shift_report(shift_report_id)

    def get_total_sum_by_estimate_for_shift_report(
        self, shift_report_id: UUID
    ) -> int | float:
        return self.reports_manager.get_total_sum_by_estimate_for_shift_report(
            shift_report_id
        )

    def get_project_stats(self, project_id: UUID) -> dict:
        if self.statistics is None:
            return {}
        return self.statistics.get_project_stats(project_id)

    def create_shift_report_detail(
        self, command: CreateShiftReportDetailPayload
    ) -> ShiftReportDetail:
        created = self.details_manager.add_shift_report_deatails(
            created_by=command.created_by,
            shift_report=command.shift_report,
            project_work=command.project_work,
            work=command.work,
            quantity=command.quantity,
        )
        record = normalize_result(created)
        if record is None:
            raise ValueError("Shift report detail creation did not return a record")
        entity = shift_report_detail_dict_to_entity(record)
        self._recalculate(entity.shift_report_project)
        return entity

    def get_shift_report_detail(
        self, shift_report_detail_id: UUID
    ) -> ShiftReportDetail | None:
        record = normalize_result(
            self.details_manager.get_by_id(shift_report_detail_id)
        )
        if record is None:
            return None
        return shift_report_detail_dict_to_entity(record)

    def update_shift_report_detail(
        self, command: UpdateShiftReportDetailCommand
    ) -> ShiftReportDetail | None:
        current = self.get_shift_report_detail(command.shift_report_detail_id)
        updated = self.details_manager.update_shift_report_details(
            shift_report_detail_id=command.shift_report_detail_id,
            shift_report=command.shift_report,
            project_work=command.project_work,
            work=command.work,
            quantity=command.quantity,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        entity = shift_report_detail_dict_to_entity(record)
        self._recalculate(
            current.shift_report_project if current else None,
            entity.shift_report_project,
        )
        return entity

    def delete_shift_report_detail(self, shift_report_detail_id: UUID) -> bool:
        current = self.get_shift_report_detail(shift_report_detail_id)
        deleted = self.details_manager.delete(shift_report_detail_id)
        if deleted is not None:
            self._recalculate(current.shift_report_project if current else None)
        return deleted is not None

    def list_shift_report_details(self, **filters) -> list[ShiftReportDetail]:
        records = self.details_manager.get_all_filtered(**filters)
        return [shift_report_detail_dict_to_entity(item) for item in records]
