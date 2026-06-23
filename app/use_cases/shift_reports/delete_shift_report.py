from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_reports import ShiftReportForbiddenError, ShiftReportNotFoundError

from .dto import ShiftReportActor, UpdateShiftReportCommand
from .ports import ShiftReportRepository


@dataclass(slots=True)
class SoftDeleteShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(self, shift_report_id: UUID, actor: ShiftReportActor) -> bool:
        current = self.repository.get_shift_report(shift_report_id)
        if current is None:
            raise ShiftReportNotFoundError("Shift report not found")
        if actor.role == "user" and current.user != actor.user_id:
            raise ShiftReportForbiddenError("User cannot soft delete not his shift report")
        if actor.role == "user" and current.signed is True:
            raise ShiftReportForbiddenError("User cannot soft delete signed shift report")
        updated = self.repository.update_shift_report(
            UpdateShiftReportCommand(
                shift_report_id=shift_report_id,
                deleted=True,
            )
        )
        if updated is None:
            raise ShiftReportNotFoundError("Shift report not found")
        return True


@dataclass(slots=True)
class DeleteShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(self, shift_report_id: UUID, actor: ShiftReportActor) -> bool:
        current = self.repository.get_shift_report(shift_report_id)
        if current is None:
            raise ShiftReportNotFoundError("Shift report not found")
        if actor.role == "user" and current.user != actor.user_id:
            raise ShiftReportForbiddenError("User cannot hard delete not his shift report")
        if actor.role == "user" and current.signed is True:
            raise ShiftReportForbiddenError("User cannot hard delete signed shift report")
        deleted = self.repository.delete_shift_report(shift_report_id)
        if not deleted:
            raise ShiftReportNotFoundError("Shift report not found")
        return deleted
