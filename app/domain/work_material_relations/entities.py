from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from .errors import WorkMaterialRelationValidationError


@dataclass(frozen=True, slots=True)
class WorkMaterialRelation:
    work_material_relation_id: UUID
    work: UUID
    material: UUID
    quantity: Decimal
    created_by: UUID
    created_at: int

    def __post_init__(self) -> None:
        if Decimal(str(self.quantity)) < 0:
            raise WorkMaterialRelationValidationError(
                "Work material relation quantity must be non-negative."
            )
        object.__setattr__(self, "quantity", Decimal(str(self.quantity)))
        object.__setattr__(self, "created_at", int(self.created_at))

    def with_updates(self, **changes) -> "WorkMaterialRelation":
        return replace(self, **changes)
