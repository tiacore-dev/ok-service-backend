from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.shift_reports import (
    ShiftReport,
    ShiftReportForbiddenError,
    ShiftReportNotFoundError,
)

from .dto import ShiftReportActor, UpdateShiftReportCommand
from .ports import ShiftReportRepository


@dataclass(slots=True)
class UpdateShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(
        self, command: UpdateShiftReportCommand, actor: ShiftReportActor
    ) -> ShiftReport:
        if actor.role == "user" and command.deleted is True:
            raise ShiftReportForbiddenError("User cannot delete shift report")
        current = self.repository.get_shift_report(command.shift_report_id)
        if current is None:
            raise ShiftReportNotFoundError("Shift report not found")
        if actor.role == "user" and current.user != actor.user_id:
            raise ShiftReportForbiddenError("User cannot edit not his shift report")
        if actor.role == "user" and current.signed is True:
            raise ShiftReportForbiddenError("User cannot edit signed shift report")
        if actor.role == "user":
            command = replace(command, user=actor.user_id)
        command = replace(command, updated_by=actor.user_id)
        updated = self.repository.update_shift_report(command)
        if updated is None:
            raise ShiftReportNotFoundError("Shift report not found")
        return updated
