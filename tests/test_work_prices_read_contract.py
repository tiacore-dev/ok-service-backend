from uuid import uuid4

import pytest
from marshmallow import ValidationError

from app.adapters.work_prices import work_price_dict_to_response
from app.schemas.work_price_schemas import WorkPriceEditSchema


def test_work_price_response_keeps_legacy_null_required_values():
    work_price_id = uuid4()
    payload = {
        "work_price_id": work_price_id,
        "work": uuid4(),
        "category": None,
        "price": None,
        "created_by": uuid4(),
        "created_at": 1,
        "deleted": False,
    }

    result = work_price_dict_to_response(payload)

    assert result["work_price_id"] == str(work_price_id)
    assert result["category"] is None
    assert result["price"] is None


@pytest.mark.parametrize("field", ["category", "price"])
def test_work_price_edit_rejects_null_required_values(field):
    with pytest.raises(ValidationError):
        WorkPriceEditSchema().load({field: None})
