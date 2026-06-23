from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.project_materials import ProjectMaterial, ProjectMaterialValidationError


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
