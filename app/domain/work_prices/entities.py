from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from .errors import WorkPriceValidationError
from .policies import validate_work_price_category


@dataclass(frozen=True, slots=True)
class WorkPrice:
    work_price_id: UUID
    work: UUID
    category: int
    price: Decimal
    created_by: UUID
    created_at: int
    deleted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.deleted, bool):
            raise WorkPriceValidationError("Work price deleted flag must be boolean.")
        try:
            validate_work_price_category(int(self.category))
        except ValueError as error:
            raise WorkPriceValidationError(str(error)) from error

        object.__setattr__(self, "category", int(self.category))
        object.__setattr__(self, "price", Decimal(str(self.price)))
        object.__setattr__(self, "created_at", int(self.created_at))

    def with_updates(self, **changes) -> "WorkPrice":
        return replace(self, **changes)
