from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateShiftReportMaterialCommand:
    shift_report: UUID
    material: UUID
    quantity: Decimal
    created_by: UUID
    shift_report_detail: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateShiftReportMaterialCommand:
    shift_report_material_id: UUID
    shift_report: UUID | None = None
    material: UUID | None = None
    quantity: Decimal | None = None
    shift_report_detail: UUID | None = None


@dataclass(frozen=True, slots=True)
class ShiftReportMaterialListQuery:
    offset: int = 0
    limit: int | None = 1000
    sort_by: str = "created_at"
    sort_order: str = "desc"
    shift_report: UUID | None = None
    material: UUID | None = None
    shift_report_detail: UUID | None = None
    created_by: UUID | None = None
    created_at: int | None = None
