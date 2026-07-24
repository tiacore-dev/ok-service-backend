from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.shift_reports import ShiftReport, ShiftReportForbiddenError

from .dto import CreateShiftReportCommand, ShiftReportActor
from .ports import ShiftReportRepository


@dataclass(slots=True)
class CreateShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(
        self, command: CreateShiftReportCommand, actor: ShiftReportActor
    ) -> ShiftReport:
        if actor.role == "user":
            raise ShiftReportForbiddenError("User cannot create shift report")
        command = replace(command, created_by=actor.user_id)
        return self.repository.create_shift_report(command)
