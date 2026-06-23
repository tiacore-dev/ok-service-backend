from __future__ import annotations

from dataclasses import dataclass

from app.domain.shift_reports import ShiftReport

from .ports import ShiftReportRepository


@dataclass(slots=True)
class ListShiftReportsUseCase:
    repository: ShiftReportRepository

    def execute(self, **filters) -> tuple[int, list[ShiftReport]]:
        return self.repository.list_shift_reports(**filters)

