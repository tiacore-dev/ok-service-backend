from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateWorkCategoryCommand:
    name: str
    created_by: UUID
    parent_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateWorkCategoryCommand:
    work_category_id: UUID
    name: str | None = None
    deleted: bool | None = None
    parent_id: UUID | None = None
    parent_id_is_set: bool = False


@dataclass(frozen=True, slots=True)
class WorkCategoryListQuery:
    offset: int = 0
    limit: int | None = 1000
    sort_by: str = "created_at"
    sort_order: str = "desc"
    name: str | None = None
    deleted: bool | None = None
