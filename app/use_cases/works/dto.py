from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateWorkCommand:
    name: str
    category: UUID | None
    measurement_unit: UUID | None
    created_by: UUID


@dataclass(frozen=True, slots=True)
class UpdateWorkCommand:
    work_id: UUID
    name: str | None = None
    category: UUID | None = None
    measurement_unit: UUID | None = None
    deleted: bool | None = None


@dataclass(frozen=True, slots=True)
class WorkListQuery:
    offset: int = 0
    limit: int | None = 1000
    sort_by: str = "created_at"
    sort_order: str = "asc"
    name: str | None = None
    measurement_unit: UUID | None = None
    deleted: bool | None = None
