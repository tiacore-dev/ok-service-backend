from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from .errors import ProjectWorkValidationError


@dataclass(frozen=True, slots=True)
class ProjectWork:
    project_work_id: UUID
    project_work_name: str | None
    project: UUID
    work: UUID
    quantity: Decimal
    created_by: UUID
    created_at: int
    signed: bool = False
    price: Decimal | None = None
    summ: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantity", Decimal(str(self.quantity)))
        object.__setattr__(self, "created_at", int(self.created_at))
        if self.summ is not None:
            object.__setattr__(self, "summ", Decimal(str(self.summ)))
        if self.price is not None:
            object.__setattr__(self, "price", Decimal(str(self.price)))
        if self.quantity < 0:
            raise ProjectWorkValidationError("Project work quantity must be non-negative.")
        object.__setattr__(self, "signed", bool(self.signed))

    def with_updates(self, **changes) -> "ProjectWork":
        return replace(self, **changes)
