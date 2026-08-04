from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_reports import (
    ShiftReportForbiddenError,
    ShiftReportNotFoundError,
)

from .dto import ShiftReportActor, UpdateShiftReportCommand
from .ports import ShiftReportRepository


@dataclass(slots=True)
class SoftDeleteShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(self, shift_report_id: UUID, actor: ShiftReportActor) -> bool:
        if actor.role == "user":
            raise ShiftReportForbiddenError("User cannot delete shift report")
        current = self.repository.get_shift_report(shift_report_id)
        if current is None:
            raise ShiftReportNotFoundError("Shift report not found")
        updated = self.repository.update_shift_report(
            UpdateShiftReportCommand(
                shift_report_id=shift_report_id,
                deleted=True,
                updated_by=actor.user_id,
            )
        )
        if updated is None:
            raise ShiftReportNotFoundError("Shift report not found")
        return True


@dataclass(slots=True)
class DeleteShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(self, shift_report_id: UUID, actor: ShiftReportActor) -> bool:
        if actor.role == "user":
            raise ShiftReportForbiddenError("User cannot delete shift report")
        current = self.repository.get_shift_report(shift_report_id)
        if current is None:
            raise ShiftReportNotFoundError("Shift report not found")
        deleted = self.repository.delete_shift_report(shift_report_id)
        if not deleted:
            raise ShiftReportNotFoundError("Shift report not found")
        return deleted
