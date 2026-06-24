from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from .errors import ShiftReportMaterialValidationError


@dataclass(frozen=True, slots=True)
class ShiftReportMaterial:
    shift_report_material_id: UUID
    shift_report: UUID
    material: UUID
    quantity: Decimal
    created_by: UUID
    created_at: int
    shift_report_detail: UUID | None = None

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ShiftReportMaterialValidationError(
                "Shift report material quantity must be positive."
            )

    def with_updates(
        self,
        *,
        shift_report: UUID | None = None,
        material: UUID | None = None,
        quantity: Decimal | None = None,
        shift_report_detail: UUID | None = None,
    ) -> ShiftReportMaterial:
        return ShiftReportMaterial(
            shift_report_material_id=self.shift_report_material_id,
            shift_report=self.shift_report if shift_report is None else shift_report,
            material=self.material if material is None else material,
            quantity=self.quantity if quantity is None else quantity,
            created_by=self.created_by,
            created_at=self.created_at,
            shift_report_detail=self.shift_report_detail
            if shift_report_detail is None
            else shift_report_detail,
        )
