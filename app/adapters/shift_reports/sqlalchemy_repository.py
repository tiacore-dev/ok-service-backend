from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
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
            payload, created_by=command.user
        )
        record = normalize_result(created)
        if record is None:
            raise ValueError("Shift report creation did not return a record")
        return shift_report_dict_to_entity(record)

    def get_shift_report(self, shift_report_id: UUID) -> ShiftReport | None:
        record = normalize_result(self.reports_manager.get_by_id(shift_report_id))
        if record is None:
            return None
        return shift_report_dict_to_entity(record)

    def update_shift_report(
        self, command: UpdateShiftReportCommand
    ) -> ShiftReport | None:
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
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return shift_report_dict_to_entity(record)

    def delete_shift_report(self, shift_report_id: UUID) -> bool:
        deleted = self.reports_manager.delete(shift_report_id)
        return deleted is not None

    def list_shift_reports(self, **filters) -> tuple[int, list[ShiftReport]]:
        total, records = self.reports_manager.get_shift_reports_filtered(**filters)
        return total, [shift_report_dict_to_entity(item) for item in records]

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]:
        projects = self.reports_manager.get_project_ids_by_leader(user_id)
        return [UUID(str(project)) for project in projects]

    def get_total_sum_by_shift_report(self, shift_report_id: UUID) -> int | float:
        return self.reports_manager.get_total_sum_by_shift_report(shift_report_id)

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
        return shift_report_detail_dict_to_entity(record)

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
        return shift_report_detail_dict_to_entity(record)

    def delete_shift_report_detail(self, shift_report_detail_id: UUID) -> bool:
        deleted = self.details_manager.delete(shift_report_detail_id)
        return deleted is not None

    def list_shift_report_details(self, **filters) -> list[ShiftReportDetail]:
        records = self.details_manager.get_all_filtered(**filters)
        return [shift_report_detail_dict_to_entity(item) for item in records]
