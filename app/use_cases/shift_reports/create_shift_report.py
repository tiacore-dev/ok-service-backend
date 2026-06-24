from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.shift_reports import ShiftReport

from .dto import CreateShiftReportCommand, ShiftReportActor
from .ports import ShiftReportRepository


@dataclass(slots=True)
class CreateShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(
        self, command: CreateShiftReportCommand, actor: ShiftReportActor
    ) -> ShiftReport:
        if actor.role == "user":
            command = replace(command, user=actor.user_id, signed=False)
        return self.repository.create_shift_report(command)
