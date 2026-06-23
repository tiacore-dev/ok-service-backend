from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_reports import ShiftReportNotFoundError

from .ports import ShiftReportRepository


@dataclass(slots=True)
class DeleteShiftReportDetailUseCase:
    repository: ShiftReportRepository

    def execute(self, shift_report_detail_id: UUID) -> bool:
        deleted = self.repository.delete_shift_report_detail(shift_report_detail_id)
        if not deleted:
            raise ShiftReportNotFoundError("Shift report detail not found")
        return deleted

