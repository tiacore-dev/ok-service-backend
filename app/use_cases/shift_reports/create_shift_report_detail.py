from __future__ import annotations

from dataclasses import dataclass

from app.domain.shift_reports import ShiftReportDetail

from .dto import CreateShiftReportDetailPayload
from .ports import ShiftReportRepository
from .work_availability import ensure_added_details_available


@dataclass(slots=True)
class CreateShiftReportDetailUseCase:
    repository: ShiftReportRepository

    def execute(self, command: CreateShiftReportDetailPayload) -> ShiftReportDetail:
        ensure_added_details_available(self.repository, [command])
        return self.repository.create_shift_report_detail(command)

    def execute_many(
        self, commands: list[CreateShiftReportDetailPayload]
    ) -> list[ShiftReportDetail]:
        # Every item is checked before the first write, so an unavailable work
        # anywhere in the batch rejects the whole batch without partial changes.
        ensure_added_details_available(self.repository, commands)
        return [
            self.repository.create_shift_report_detail(command) for command in commands
        ]
