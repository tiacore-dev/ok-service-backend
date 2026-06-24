from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_report_materials import (
    ShiftReportMaterial,
    ShiftReportMaterialNotFoundError,
)

from .ports import ShiftReportMaterialRepository


@dataclass(slots=True)
class GetShiftReportMaterialUseCase:
    repository: ShiftReportMaterialRepository

    def execute(self, shift_report_material_id: UUID) -> ShiftReportMaterial:
        shift_report_material = self.repository.get_shift_report_material(
            shift_report_material_id
        )
        if shift_report_material is None:
            raise ShiftReportMaterialNotFoundError("Shift report material not found")
        return shift_report_material
