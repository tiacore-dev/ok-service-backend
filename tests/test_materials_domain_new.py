from uuid import uuid4

import pytest

from app.domain.materials import Material, MaterialValidationError


def test_material_rejects_empty_name():
    with pytest.raises(MaterialValidationError):
        Material(
            material_id=uuid4(),
            name="",
            measurement_unit="pcs",
            created_by=uuid4(),
            created_at=1,
        )
