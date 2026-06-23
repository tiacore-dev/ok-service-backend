from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_reports import ShiftReportDetail, ShiftReportNotFoundError

from .ports import ShiftReportRepository


@dataclass(slots=True)
class GetShiftReportDetailUseCase:
    repository: ShiftReportRepository

    def execute(self, shift_report_detail_id: UUID) -> ShiftReportDetail:
        detail = self.repository.get_shift_report_detail(shift_report_detail_id)
        if detail is None:
            raise ShiftReportNotFoundError("Shift report detail not found")
        return detail

