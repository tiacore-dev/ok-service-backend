from __future__ import annotations

ALLOWED_WORK_PRICE_CATEGORIES = frozenset({0, 1, 2, 3, 4})


def validate_work_price_category(category: int) -> None:
    if category not in ALLOWED_WORK_PRICE_CATEGORIES:
        allowed = ", ".join(str(value) for value in sorted(ALLOWED_WORK_PRICE_CATEGORIES))
        raise ValueError(f"Work price category must be one of: {allowed}")
