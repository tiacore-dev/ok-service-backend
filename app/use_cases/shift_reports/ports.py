from __future__ import annotations

from collections.abc import Collection
from typing import Protocol
from uuid import UUID

from app.domain.shift_reports import ShiftReport, ShiftReportDetail

from .dto import (
    CreateShiftReportCommand,
    CreateShiftReportDetailPayload,
    UpdateShiftReportCommand,
    UpdateShiftReportDetailCommand,
)


class ShiftWorkAvailabilityReader(Protocol):
    """Reads what is needed to decide if a work may be added to a shift.

    Availability depends on the category of the shift performer, never on the
    user who sends the request.
    """

    def get_shift_report_performer_category(
        self, shift_report_id: UUID
    ) -> int | None:
        """Category of the shift performer, or `None` if the shift is missing."""
        ...

    def get_user_categories(self, user_ids: Collection[UUID]) -> dict[UUID, int]:
        """Categories of existing users; unknown ids are absent from the result."""
        ...

    def get_unavailable_work_ids(
        self, work_ids: Collection[UUID], category: int
    ) -> set[UUID]:
        """Works whose active price for `category` is the `-1` marker."""
        ...


class ShiftReportRepository(ShiftWorkAvailabilityReader, Protocol):
    def create_shift_report(self, command: CreateShiftReportCommand) -> ShiftReport: ...

    def get_shift_report(self, shift_report_id: UUID) -> ShiftReport | None: ...

    def update_shift_report(
        self, command: UpdateShiftReportCommand
    ) -> ShiftReport | None: ...

    def sign_shift_report(
        self, shift_report_id: UUID, signed_by: UUID
    ) -> ShiftReport | None: ...

    def delete_shift_report(self, shift_report_id: UUID) -> bool: ...

    def list_shift_reports(self, **filters) -> tuple[int, list[ShiftReport]]: ...

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]: ...

    def get_total_sum_by_shift_report(
        self, shift_report_id: UUID, *, include_unsigned: bool = False
    ) -> int | float: ...

    def get_total_sum_by_estimate_for_shift_report(
        self, shift_report_id: UUID, *, include_unsigned: bool = False
    ) -> int | float: ...

    def get_project_stats(self, project_id: UUID) -> dict: ...

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


class ShiftReportBulkRepository(ShiftWorkAvailabilityReader, Protocol):
    def create_shift_reports(
        self, commands: list[CreateShiftReportCommand]
    ) -> list[ShiftReport]:
        """Create every report and its details atomically, or roll back all writes."""
        ...
