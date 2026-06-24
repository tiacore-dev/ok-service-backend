from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.domain.shift_report_materials import ShiftReportMaterial

from .dto import CreateShiftReportMaterialCommand
from .ports import ShiftReportMaterialRepository
from ..time_utils import utc_epoch_seconds


@dataclass(slots=True)
class CreateShiftReportMaterialUseCase:
    repository: ShiftReportMaterialRepository

    def execute(
        self, command: CreateShiftReportMaterialCommand
    ) -> ShiftReportMaterial:
        shift_report_material = ShiftReportMaterial(
            shift_report_material_id=uuid4(),
            shift_report=command.shift_report,
            material=command.material,
            quantity=command.quantity,
            created_by=command.created_by,
            created_at=utc_epoch_seconds(),
            shift_report_detail=command.shift_report_detail,
        )
        return self.repository.create_shift_report_material(shift_report_material)
