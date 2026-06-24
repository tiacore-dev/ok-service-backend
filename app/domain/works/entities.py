from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any
from uuid import UUID

from .errors import WorkValidationError


@dataclass(frozen=True, slots=True)
class Work:
    work_id: UUID
    name: str
    category: dict[str, Any] | None
    measurement_unit: str | None
    created_at: int
    created_by: UUID
    deleted: bool
    work_prices: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "created_at", int(self.created_at))
        object.__setattr__(self, "deleted", bool(self.deleted))
        if not self.name:
            raise WorkValidationError("Work name is required.")

    def with_updates(self, **changes) -> "Work":
        return replace(self, **changes)
