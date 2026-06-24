from uuid import uuid4

import pytest

from app.domain.works import Work, WorkValidationError


def test_work_requires_non_empty_name():
    with pytest.raises(WorkValidationError):
        Work(
            work_id=uuid4(),
            name="   ",
            category=None,
            measurement_unit=None,
            created_at=1,
            created_by=uuid4(),
            deleted=False,
        )
