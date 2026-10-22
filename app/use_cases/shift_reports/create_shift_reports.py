from dataclasses import dataclass

from app.domain.shift_reports import ShiftReport, ShiftReportValidationError

from .create_shift_report import CreateShiftReportUseCase
from .dto import CreateShiftReportCommand, ShiftReportActor
from .ports import ShiftReportBulkRepository


@dataclass(slots=True)
class CreateShiftReportsUseCase:
    repository: ShiftReportBulkRepository

    def execute(
        self, commands: list[CreateShiftReportCommand], actor: ShiftReportActor
    ) -> list[ShiftReport]:
        if not commands:
            raise ShiftReportValidationError("user_ids must not be empty")
        unique_commands = {}
        for command in commands:
            prepared = CreateShiftReportUseCase.prepare(command, actor)
            unique_commands.setdefault(prepared.user, prepared)
        return self.repository.create_shift_reports(list(unique_commands.values()))
