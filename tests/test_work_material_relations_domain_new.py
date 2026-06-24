from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.work_material_relations import (
    WorkMaterialRelation,
    WorkMaterialRelationValidationError,
)


def test_work_material_relation_rejects_negative_quantity():
    with pytest.raises(WorkMaterialRelationValidationError):
        WorkMaterialRelation(
            work_material_relation_id=uuid4(),
            work=uuid4(),
            material=uuid4(),
            quantity=Decimal("-1"),
            created_by=uuid4(),
            created_at=1,
        )
