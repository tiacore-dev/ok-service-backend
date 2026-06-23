from __future__ import annotations

from dataclasses import dataclass

from app.domain.shift_reports import ShiftReportDetail, ShiftReportNotFoundError

from .dto import UpdateShiftReportDetailCommand
from .ports import ShiftReportRepository


@dataclass(slots=True)
class UpdateShiftReportDetailUseCase:
    repository: ShiftReportRepository

    def execute(self, command: UpdateShiftReportDetailCommand) -> ShiftReportDetail:
        updated = self.repository.update_shift_report_detail(command)
        if updated is None:
            raise ShiftReportNotFoundError("Shift report detail not found")
        return updated

