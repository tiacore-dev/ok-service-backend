from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProjectWorkActor:
    role: str
    user_id: UUID


@dataclass(frozen=True, slots=True)
class CreateProjectWorkCommand:
    project: UUID
    project_work_name: str | None
    work: UUID
    quantity: Decimal
    summ: Decimal | None = None
    signed: bool | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class BulkCreateProjectWorksCommand:
    project_works: list[CreateProjectWorkCommand]


@dataclass(frozen=True, slots=True)
class UpdateProjectWorkCommand:
    project_work_id: UUID
    project: UUID | None = None
    project_work_name: str | None = None
    work: UUID | None = None
    quantity: Decimal | None = None
    summ: Decimal | None = None
    signed: bool | None = None


@dataclass(frozen=True, slots=True)
class ProjectWorkListQuery:
    offset: int = 0
    limit: int | None = 1000
    sort_by: str = "created_at"
    sort_order: str = "desc"
    signed: bool | None = None
    work: UUID | None = None
    project: UUID | None = None
    project_work_name: str | None = None
    min_quantity: Decimal | None = None
    max_quantity: Decimal | None = None
    min_summ: Decimal | None = None
    max_summ: Decimal | None = None
