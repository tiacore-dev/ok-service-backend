from __future__ import annotations

from dataclasses import dataclass

from app.domain.shift_reports import ShiftReportDetail

from .dto import CreateShiftReportDetailPayload
from .ports import ShiftReportRepository


@dataclass(slots=True)
class CreateShiftReportDetailUseCase:
    repository: ShiftReportRepository

    def execute(self, command: CreateShiftReportDetailPayload) -> ShiftReportDetail:
        return self.repository.create_shift_report_detail(command)

