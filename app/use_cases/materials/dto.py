from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateMaterialCommand:
    name: str
    created_by: UUID
    measurement_unit: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateMaterialCommand:
    material_id: UUID
    name: str | None = None
    measurement_unit: str | None = None
    deleted: bool | None = None


@dataclass(frozen=True, slots=True)
class MaterialListQuery:
    offset: int = 0
    limit: int | None = 1000
    sort_by: str = "created_at"
    sort_order: str = "desc"
    name: str | None = None
    measurement_unit: str | None = None
    deleted: bool | None = None
