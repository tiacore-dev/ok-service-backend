from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateWorkMaterialRelationCommand:
    work: UUID
    material: UUID
    quantity: Decimal
    created_by: UUID


@dataclass(frozen=True, slots=True)
class UpdateWorkMaterialRelationCommand:
    work_material_relation_id: UUID
    work: UUID | None = None
    material: UUID | None = None
    quantity: Decimal | None = None


@dataclass(frozen=True, slots=True)
class WorkMaterialRelationListQuery:
    offset: int = 0
    limit: int | None = 1000
    sort_by: str = "created_at"
    sort_order: str = "desc"
    work: UUID | None = None
    material: UUID | None = None
    created_by: UUID | None = None
    created_at: int | None = None
