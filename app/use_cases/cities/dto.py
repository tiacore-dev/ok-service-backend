from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCityCommand:
    name: str
    created_by: UUID


@dataclass(frozen=True, slots=True)
class UpdateCityCommand:
    city_id: UUID
    has_name: bool = False
    name: str | None = None
    has_deleted: bool = False
    deleted: bool | None = None


@dataclass(frozen=True, slots=True)
class CityListQuery:
    offset: int = 0
    limit: int = 1000
    sort_by: str | None = None
    sort_order: str = "desc"
    name: str | None = None
    deleted: bool | None = None
