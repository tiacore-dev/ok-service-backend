from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ObjectActor:
    role: str
    user_id: UUID


@dataclass(frozen=True, slots=True)
class CreateObjectCommand:
    name: str
    address: str | None = None
    description: str | None = None
    manager: UUID | None = None
    status: str | None = None
    city: UUID | None = None
    lng: float | None = None
    ltd: float | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateObjectCommand:
    object_id: UUID
    name: str | None = None
    address: str | None = None
    description: str | None = None
    status: str | None = None
    manager: UUID | None = None
    deleted: bool | None = None
    city: UUID | None = None
    lng: float | None = None
    ltd: float | None = None


@dataclass(frozen=True, slots=True)
class ObjectListQuery:
    offset: int = 0
    limit: int = 10
    sort_by: str | None = None
    sort_order: str = "desc"
    address: str | None = None
    status: str | None = None
    name: str | None = None
    manager: UUID | None = None
    deleted: bool | None = None
    city: UUID | None = None
    lng: float | None = None
    ltd: float | None = None
    created_by: UUID | None = None
    created_at: int | None = None


@dataclass(frozen=True, slots=True)
class ObjectStatsListQuery:
    offset: int = 0
    limit: int = 10
    search: str | None = None
