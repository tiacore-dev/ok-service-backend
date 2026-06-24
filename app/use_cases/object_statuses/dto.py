from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ObjectStatusListQuery:
    offset: int = 0
    limit: int = 10
    sort_by: str | None = None
    sort_order: str = "desc"
    object_status_id: str | None = None
    name: str | None = None
