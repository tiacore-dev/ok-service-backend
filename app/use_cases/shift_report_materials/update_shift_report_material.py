from __future__ import annotations

from dataclasses import dataclass

from app.domain.shift_report_materials import (
    ShiftReportMaterial,
    ShiftReportMaterialNotFoundError,
    validate_shift_report_material_quantity,
)

from .dto import UpdateShiftReportMaterialCommand
from .ports import ShiftReportMaterialRepository


@dataclass(slots=True)
class UpdateShiftReportMaterialUseCase:
    repository: ShiftReportMaterialRepository

    def execute(self, command: UpdateShiftReportMaterialCommand) -> ShiftReportMaterial:
        current = self.repository.get_shift_report_material(
            command.shift_report_material_id
        )
        if current is None:
            raise ShiftReportMaterialNotFoundError("Shift report material not found")

        shift_report = command.shift_report
        material = command.material
        quantity = command.quantity
        shift_report_detail = command.shift_report_detail

        if (
            shift_report is None
            and material is None
            and quantity is None
            and shift_report_detail is None
        ):
            return current

        if command.quantity is not None:
            validate_shift_report_material_quantity(command.quantity)

        updated = current.with_updates(
            shift_report=shift_report,
            material=material,
            quantity=quantity,
            shift_report_detail=shift_report_detail,
        )
        result = self.repository.update_shift_report_material(updated)
        if result is None:
            raise ShiftReportMaterialNotFoundError("Shift report material not found")
        return result
