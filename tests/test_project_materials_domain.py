from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.project_materials import (
    ProjectMaterial,
    ProjectMaterialInUseError,
    ProjectMaterialValidationError,
)
from app.domain.project_materials.policies import (
    ensure_project_material_identity_unchanged,
)


def test_project_material_rejects_non_positive_quantity():
    with pytest.raises(ProjectMaterialValidationError):
        ProjectMaterial(
            project_material_id=uuid4(),
            project=uuid4(),
            material=uuid4(),
            quantity=Decimal("0"),
            created_by=uuid4(),
            created_at=1,
        )


@pytest.mark.parametrize("field", [0, 1, 2])
def test_used_project_material_identity_cannot_change(field):
    current = (uuid4(), uuid4(), uuid4())
    changed = list(current)
    changed[field] = uuid4()
    with pytest.raises(ProjectMaterialInUseError):
        ensure_project_material_identity_unchanged(
            used=True,
            current_identity=current,
            target_identity=(changed[0], changed[1], changed[2]),
        )


def test_unused_project_material_identity_can_change():
    ensure_project_material_identity_unchanged(
        used=False,
        current_identity=(uuid4(), uuid4(), uuid4()),
        target_identity=(uuid4(), uuid4(), None),
    )


def test_used_project_material_allows_unchanged_identity():
    identity = (uuid4(), uuid4(), uuid4())
    ensure_project_material_identity_unchanged(
        used=True,
        current_identity=identity,
        target_identity=identity,
    )
