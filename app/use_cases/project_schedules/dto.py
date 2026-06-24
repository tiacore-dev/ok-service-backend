from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProjectScheduleActor:
    role: str
    user_id: UUID


@dataclass(frozen=True, slots=True)
class CreateProjectScheduleCommand:
    project: UUID
    work: UUID
    quantity: float
    date: int | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateProjectScheduleCommand:
    project_schedule_id: UUID
    project: UUID | None = None
    work: UUID | None = None
    quantity: float | None = None
    date: int | None = None


@dataclass(frozen=True, slots=True)
class ProjectScheduleListQuery:
    offset: int = 0
    limit: int = 10
    sort_by: str | None = None
    sort_order: str = "desc"
    work: UUID | None = None
    project: UUID | None = None
    date: int | None = None
