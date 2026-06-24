from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.shift_report_materials import (
    ShiftReportMaterial,
    ShiftReportMaterialValidationError,
)


def test_shift_report_material_rejects_non_positive_quantity():
    with pytest.raises(ShiftReportMaterialValidationError):
        ShiftReportMaterial(
            shift_report_material_id=uuid4(),
            shift_report=uuid4(),
            material=uuid4(),
            quantity=Decimal("0"),
            created_by=uuid4(),
            created_at=1,
        )
