from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.shift_report_materials import (
    ShiftReportMaterial,
    ShiftReportMaterialValidationError,
    validate_shift_report_material_quantity,
)


def test_shift_report_material_can_represent_legacy_non_positive_quantity():
    material = ShiftReportMaterial(
        shift_report_material_id=uuid4(),
        shift_report=uuid4(),
        material=uuid4(),
        quantity=Decimal("0"),
        created_by=uuid4(),
        created_at=1,
    )

    assert material.quantity == Decimal("0")


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("-0.01"),
    ],
)
def test_validate_shift_report_material_quantity_rejects_non_positive(
    quantity: Decimal,
):
    with pytest.raises(
        ShiftReportMaterialValidationError,
        match="Shift report material quantity must be positive",
    ):
        validate_shift_report_material_quantity(quantity)


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0.01"),
        Decimal("1"),
        Decimal("10.50"),
    ],
)
def test_validate_shift_report_material_quantity_accepts_positive(
    quantity: Decimal,
):
    validate_shift_report_material_quantity(quantity)
