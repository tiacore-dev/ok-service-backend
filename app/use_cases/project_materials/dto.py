from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateProjectMaterialCommand:
    project: UUID
    material: UUID
    quantity: Decimal
    created_by: UUID
    project_work: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateProjectMaterialCommand:
    project_material_id: UUID
    project: UUID | None = None
    project_is_set: bool = False
    material: UUID | None = None
    material_is_set: bool = False
    quantity: Decimal | None = None
    quantity_is_set: bool = False
    project_work: UUID | None = None
    project_work_is_set: bool = False


@dataclass(frozen=True, slots=True)
class ProjectMaterialListQuery:
    offset: int = 0
    limit: int | None = 1000
    sort_by: str = "created_at"
    sort_order: str = "desc"
    project: UUID | None = None
    material: UUID | None = None
    project_work: UUID | None = None
