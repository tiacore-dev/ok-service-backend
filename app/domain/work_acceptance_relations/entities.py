from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from .errors import WorkAcceptanceRelationValidationError


@dataclass(frozen=True, slots=True)
class WorkAcceptanceRelation:
    id: UUID
    acceptance_id: UUID
    work_id: UUID
    quantity: Decimal

    def __post_init__(self) -> None:
        quantity = Decimal(str(self.quantity))
        if quantity <= 0:
            raise WorkAcceptanceRelationValidationError(
                "Work acceptance relation quantity must be positive."
            )
        object.__setattr__(self, "quantity", quantity)

    def with_updates(self, **changes) -> "WorkAcceptanceRelation":
        return replace(self, **changes)
