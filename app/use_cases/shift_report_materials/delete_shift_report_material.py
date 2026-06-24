from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_report_materials import ShiftReportMaterialNotFoundError

from .ports import ShiftReportMaterialRepository


@dataclass(slots=True)
class DeleteShiftReportMaterialUseCase:
    repository: ShiftReportMaterialRepository

    def execute(self, shift_report_material_id: UUID) -> bool:
        current = self.repository.get_shift_report_material(shift_report_material_id)
        if current is None:
            raise ShiftReportMaterialNotFoundError("Shift report material not found")

        deleted = self.repository.delete_shift_report_material(shift_report_material_id)
        if not deleted:
            raise ShiftReportMaterialNotFoundError("Shift report material not found")
        return deleted
