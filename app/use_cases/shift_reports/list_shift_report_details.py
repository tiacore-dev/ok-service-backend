from __future__ import annotations

from dataclasses import dataclass

from app.domain.shift_reports import ShiftReportDetail

from .ports import ShiftReportRepository


@dataclass(slots=True)
class ListShiftReportDetailsUseCase:
    repository: ShiftReportRepository

    def execute(self, **filters) -> list[ShiftReportDetail]:
        return self.repository.list_shift_report_details(**filters)

