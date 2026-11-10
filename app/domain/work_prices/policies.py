from __future__ import annotations

from decimal import Decimal, InvalidOperation

ALLOWED_WORK_PRICE_CATEGORIES = frozenset({0, 1, 2, 3, 4})

# `-1` is a business marker, not an amount: the work is unavailable for the
# performer category. It must never take part in payment calculations.
UNAVAILABLE_WORK_PRICE = Decimal(-1)

WORK_UNAVAILABLE_FOR_CATEGORY_MESSAGE = "Работа недоступна для категории исполнителя"

WORK_PRICE_VALUE_ERROR_MESSAGE = (
    "Work price must be greater than or equal to 0, "
    "or exactly -1 (work is unavailable for the category)."
)


def validate_work_price_category(category: int) -> None:
    if category not in ALLOWED_WORK_PRICE_CATEGORIES:
        allowed = ", ".join(str(value) for value in sorted(ALLOWED_WORK_PRICE_CATEGORIES))
        raise ValueError(f"Work price category must be one of: {allowed}")


def _to_decimal(price: Decimal | float | str) -> Decimal:
    try:
        value = Decimal(str(price))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(WORK_PRICE_VALUE_ERROR_MESSAGE) from error
    if not value.is_finite():
        raise ValueError(WORK_PRICE_VALUE_ERROR_MESSAGE)
    return value


def validate_work_price_value(price: Decimal | float | str) -> None:
    """Allow payment amounts `>= 0` and the `-1` unavailability marker."""
    value = _to_decimal(price)
    if value >= 0 or value == UNAVAILABLE_WORK_PRICE:
        return
    raise ValueError(WORK_PRICE_VALUE_ERROR_MESSAGE)


def is_unavailable_work_price(price: Decimal | float | str | None) -> bool:
    if price is None:
        return False
    try:
        return _to_decimal(price) == UNAVAILABLE_WORK_PRICE
    except ValueError:
        return False
