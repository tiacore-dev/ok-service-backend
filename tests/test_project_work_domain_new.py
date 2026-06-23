from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.project_works import ProjectWork, ProjectWorkValidationError


def test_project_work_rejects_negative_quantity():
    with pytest.raises(ProjectWorkValidationError):
        ProjectWork(
            project_work_id=uuid4(),
            project_work_name="Test work",
            project=uuid4(),
            work=uuid4(),
            quantity=Decimal("-1"),
            summ=None,
            created_by=uuid4(),
            created_at=1,
        )
