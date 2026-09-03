from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.domain.projects import ProjectStatus


@dataclass(frozen=True, slots=True)
class ProjectActor:
    role: str
    user_id: UUID


@dataclass(frozen=True, slots=True)
class CreateProjectCommand:
    name: str
    object: UUID
    project_leader: UUID | None = None
    night_shift_available: bool = False
    extreme_conditions_available: bool = False
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateProjectCommand:
    project_id: UUID
    name: str | None = None
    object: UUID | None = None
    project_leader: UUID | None = None
    night_shift_available: bool | None = None
    extreme_conditions_available: bool | None = None
    deleted: bool | None = None


@dataclass(frozen=True, slots=True)
class ProjectListQuery:
    offset: int = 0
    limit: int = 10
    sort_by: str | None = None
    sort_order: str = "desc"
    name: str | None = None
    deleted: bool | None = None
    object: UUID | None = None
    project_leader: UUID | None = None
    created_by: UUID | None = None
    created_at: int | None = None
    status: ProjectStatus | None = None


@dataclass(frozen=True, slots=True)
class ProjectLeaderStatsListQuery:
    offset: int = 0
    limit: int = 10
    search: str | None = None


ProjectStatsMap = dict[str, dict[str, Any]]
