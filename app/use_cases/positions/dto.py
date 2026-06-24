from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreatePositionCommand:
    name: str
    created_by: UUID


@dataclass(frozen=True, slots=True)
class UpdatePositionCommand:
    position_id: UUID
    name: str | None = None


@dataclass(frozen=True, slots=True)
class PositionListQuery:
    offset: int = 0
    limit: int = 1000
    sort_by: str | None = None
    sort_order: str = "desc"
    name: str | None = None
