from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_reports import ShiftReport, ShiftReportNotFoundError

from .ports import ShiftReportRepository


@dataclass(slots=True)
class GetShiftReportUseCase:
    repository: ShiftReportRepository

    def execute(self, shift_report_id: UUID) -> ShiftReport:
        shift_report = self.repository.get_shift_report(shift_report_id)
        if shift_report is None:
            raise ShiftReportNotFoundError("Shift report not found")
        return shift_report

