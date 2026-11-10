"""Allowed work price values: `>= 0` or exactly `-1` (work unavailable)."""

from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

import pytest
from marshmallow import ValidationError

from app.domain.work_prices import (
    WorkPrice,
    WorkPriceValidationError,
    is_unavailable_work_price,
    validate_work_price_value,
)
from app.schemas.work_price_schemas import WorkPriceCreateSchema, WorkPriceEditSchema
from app.use_cases.work_prices import (
    CreateWorkPriceCommand,
    CreateWorkPriceUseCase,
    UpdateWorkPriceCommand,
    UpdateWorkPriceUseCase,
)

VALID = [Decimal("-1"), Decimal("-1.00"), Decimal("0"), Decimal("0.01"), Decimal("250.5")]
INVALID = [Decimal("-2"), Decimal("-1.01"), Decimal("-0.99"), Decimal("-0.01"), Decimal("-100")]


@pytest.mark.parametrize("price", VALID)
def test_domain_accepts_minus_one_zero_and_positive(price):
    validate_work_price_value(price)


@pytest.mark.parametrize("price", INVALID)
def test_domain_rejects_values_below_zero_except_minus_one(price):
    with pytest.raises(ValueError):
        validate_work_price_value(price)


@pytest.mark.parametrize("price", ["nan", "inf", "-inf"])
def test_domain_rejects_non_finite_values(price):
    with pytest.raises(ValueError):
        validate_work_price_value(price)


def test_unavailable_marker_is_only_minus_one():
    assert is_unavailable_work_price(Decimal("-1.00"))
    assert is_unavailable_work_price(-1)
    assert not is_unavailable_work_price(0)
    assert not is_unavailable_work_price(Decimal("100"))
    assert not is_unavailable_work_price(None)


@pytest.mark.parametrize("price", [-1, 0, 0.5, 100])
def test_schemas_accept_allowed_prices(price):
    work = str(uuid4())
    schema = WorkPriceCreateSchema()
    # `work` existence is validated against the DB; check only `price` here.
    assert "price" not in schema.validate({"work": work, "category": 1, "price": price})
    loaded = cast(dict[str, Any], WorkPriceEditSchema(only=("price",)).load({"price": price}))
    assert loaded["price"] == price


@pytest.mark.parametrize("price", [-2, -1.5, -0.5, -0.01])
def test_schemas_reject_values_below_minus_one_and_between(price):
    errors = WorkPriceCreateSchema().validate(
        {"work": str(uuid4()), "category": 1, "price": price}
    )
    assert "price" in errors
    with pytest.raises(ValidationError):
        WorkPriceEditSchema(only=("price",)).load({"price": price})


class _Repository:
    def __init__(self, current: WorkPrice | None = None):
        self.current = current
        self.created: WorkPrice | None = None
        self.updated: WorkPrice | None = None

    def create_work_price(self, work_price):
        self.created = work_price
        return work_price

    def get_work_price(self, work_price_id):
        return self.current

    def get_work_price_record(self, work_price_id):
        return None

    def update_work_price(self, work_price):
        self.updated = work_price
        return work_price

    def delete_work_price(self, work_price_id):
        return False

    def list_work_prices(self, query):
        return []

    def list_work_price_records(self, query):
        return []


def _existing(price: Decimal) -> WorkPrice:
    return WorkPrice(
        work_price_id=uuid4(),
        work=uuid4(),
        category=1,
        price=price,
        created_by=uuid4(),
        created_at=1,
    )


@pytest.mark.parametrize("price", VALID)
def test_create_use_case_stores_allowed_prices(price):
    repository = _Repository()
    result = CreateWorkPriceUseCase(repository=repository).execute(
        CreateWorkPriceCommand(work=uuid4(), category=2, price=price, created_by=uuid4())
    )
    assert result.price == price
    assert repository.created is not None


@pytest.mark.parametrize("price", INVALID)
def test_create_use_case_rejects_values_below_minus_one(price):
    repository = _Repository()
    with pytest.raises(WorkPriceValidationError):
        CreateWorkPriceUseCase(repository=repository).execute(
            CreateWorkPriceCommand(
                work=uuid4(), category=2, price=price, created_by=uuid4()
            )
        )
    assert repository.created is None


@pytest.mark.parametrize("price", VALID)
def test_update_use_case_accepts_allowed_prices(price):
    current = _existing(Decimal("10"))
    repository = _Repository(current)
    result = UpdateWorkPriceUseCase(repository=repository).execute(
        UpdateWorkPriceCommand(work_price_id=current.work_price_id, price=price)
    )
    assert result.price == price


@pytest.mark.parametrize("price", INVALID)
def test_update_use_case_rejects_values_below_minus_one(price):
    current = _existing(Decimal("10"))
    repository = _Repository(current)
    with pytest.raises(WorkPriceValidationError):
        UpdateWorkPriceUseCase(repository=repository).execute(
            UpdateWorkPriceCommand(work_price_id=current.work_price_id, price=price)
        )
    assert repository.updated is None


def test_use_case_does_not_revalidate_unchanged_legacy_price():
    """A stored price is validated only when the request changes it."""
    current = _existing(Decimal("-5"))
    repository = _Repository(current)
    result = UpdateWorkPriceUseCase(repository=repository).execute(
        UpdateWorkPriceCommand(work_price_id=current.work_price_id, category=3)
    )
    assert result.price == Decimal("-5")
    assert result.category == 3


@pytest.mark.parametrize("category", [0, 1])
def test_model_to_dict_keeps_zero_category_and_price(category):
    """`0` is a valid category and price; it must not serialize as `null`."""
    from app.database.models import WorkPrices

    record = WorkPrices(
        work_price_id=uuid4(),
        work=uuid4(),
        category=category,
        price=Decimal("0"),
        created_by=uuid4(),
        created_at=1,
        deleted=False,
    )
    payload = record.to_dict()
    assert payload["category"] == category
    assert payload["price"] == Decimal("0")
