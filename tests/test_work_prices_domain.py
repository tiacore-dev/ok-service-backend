from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.work_prices import WorkPrice, WorkPriceValidationError


def test_work_price_rejects_invalid_category():
    with pytest.raises(WorkPriceValidationError):
        WorkPrice(
            work_price_id=uuid4(),
            work=uuid4(),
            category=99,
            price=Decimal("100.00"),
            created_by=uuid4(),
            created_at=1,
        )
