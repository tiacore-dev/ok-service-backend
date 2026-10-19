from decimal import Decimal
from uuid import UUID

from .errors import ShiftReportMaterialValidationError


def validate_shift_material_links(
    *,
    shift_project: UUID,
    material_project: UUID,
    shift_report: UUID,
    detail_report: UUID | None,
    material_work: UUID | None,
    detail_work: UUID | None,
) -> None:
    if shift_project != material_project:
        raise ShiftReportMaterialValidationError(
            "Project material must belong to the shift report project"
        )
    if detail_report is not None:
        if detail_report != shift_report:
            raise ShiftReportMaterialValidationError(
                "Detail must belong to the same shift report"
            )
        if detail_work != material_work:
            raise ShiftReportMaterialValidationError(
                "Project material must match the detail project_work"
            )


def normalize_material_quantity(quantity: Decimal, unit: str | None) -> Decimal:
    if unit is not None and unit.strip().lower() == "шт.":
        quantity = Decimal(int(quantity))
    if quantity <= 0:
        raise ShiftReportMaterialValidationError(
            "Shift report material quantity must be positive."
        )
    return quantity
