from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from .errors import ProjectMaterialValidationError


@dataclass(frozen=True, slots=True)
class ProjectMaterial:
    project_material_id: UUID
    project: UUID
    material: UUID
    quantity: Decimal
    created_by: UUID
    created_at: int
    project_work: UUID | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantity", Decimal(str(self.quantity)))
        object.__setattr__(self, "created_at", int(self.created_at))
        if self.quantity <= 0:
            raise ProjectMaterialValidationError("Project material quantity must be positive.")

    def with_updates(self, **changes) -> "ProjectMaterial":
        return replace(self, **changes)
