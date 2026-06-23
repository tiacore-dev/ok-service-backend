from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.shift_reports import ShiftReport, ShiftReportDetail

from .dto import (
    CreateShiftReportCommand,
    CreateShiftReportDetailPayload,
    UpdateShiftReportCommand,
    UpdateShiftReportDetailCommand,
)


class ShiftReportRepository(Protocol):
    def create_shift_report(self, command: CreateShiftReportCommand) -> ShiftReport: ...

    def get_shift_report(self, shift_report_id: UUID) -> ShiftReport | None: ...

    def update_shift_report(self, command: UpdateShiftReportCommand) -> ShiftReport | None: ...

    def delete_shift_report(self, shift_report_id: UUID) -> bool: ...

    def list_shift_reports(self, **filters) -> tuple[int, list[ShiftReport]]: ...

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]: ...

    def get_total_sum_by_shift_report(self, shift_report_id: UUID) -> int | float: ...

    def create_shift_report_detail(
        self, command: CreateShiftReportDetailPayload
    ) -> ShiftReportDetail: ...

    def get_shift_report_detail(
        self, shift_report_detail_id: UUID
    ) -> ShiftReportDetail | None: ...

    def update_shift_report_detail(
        self, command: UpdateShiftReportDetailCommand
    ) -> ShiftReportDetail | None: ...

    def delete_shift_report_detail(self, shift_report_detail_id: UUID) -> bool: ...

    def list_shift_report_details(self, **filters) -> list[ShiftReportDetail]: ...

