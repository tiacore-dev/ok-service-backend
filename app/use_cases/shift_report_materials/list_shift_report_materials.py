from __future__ import annotations

from dataclasses import dataclass

from app.domain.shift_report_materials import ShiftReportMaterial

from .dto import ShiftReportMaterialListQuery
from .ports import ShiftReportMaterialRepository


@dataclass(slots=True)
class ListShiftReportMaterialsUseCase:
    repository: ShiftReportMaterialRepository

    def execute(self, query: ShiftReportMaterialListQuery) -> list[ShiftReportMaterial]:
        return self.repository.list_shift_report_materials(query)
