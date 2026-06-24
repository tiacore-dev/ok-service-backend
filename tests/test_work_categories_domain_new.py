from uuid import uuid4

import pytest

from app.domain.work_categories import WorkCategory, WorkCategoryValidationError


def test_work_category_rejects_empty_name():
    with pytest.raises(WorkCategoryValidationError):
        WorkCategory(
            work_category_id=uuid4(),
            name="   ",
            created_by=uuid4(),
            created_at=1,
        )
