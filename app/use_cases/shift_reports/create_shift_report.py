from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.shift_reports import (
    ShiftReport,
    ShiftReportForbiddenError,
    ShiftReportValidationError,
)

from .dto import (
    SHORT_SHIFT_EDITOR_ROLES,
    CreateShiftReportCommand,
    ShiftReportActor,
)
from .ports import ShiftReportRepository


@dataclass(slots=True)
class CreateShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(
        self, command: CreateShiftReportCommand, actor: ShiftReportActor
    ) -> ShiftReport:
        if actor.role == "user":
            raise ShiftReportForbiddenError("User cannot create shift report")
        if (
            command.short_shift is not None
            and actor.role not in SHORT_SHIFT_EDITOR_ROLES
        ):
            raise ShiftReportForbiddenError(
                "Only admin, manager, and project leader can set short_shift"
            )
        if (
            command.date_start is not None
            and command.date_end is not None
            and command.date_end < command.date_start
        ):
            raise ShiftReportValidationError(
                "Shift report date_end must be greater than or equal to date_start."
            )
        command = replace(command, created_by=actor.user_id)
        return self.repository.create_shift_report(command)
