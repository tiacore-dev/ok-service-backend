from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from .errors import PositionValidationError


@dataclass(frozen=True, slots=True)
class Position:
    position_id: UUID
    name: str
    created_by: UUID | None
    created_at: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "created_at", int(self.created_at))
        if not self.name:
            raise PositionValidationError("Position name is required.")

    def with_updates(self, *, name: str | None = None) -> "Position":
        return replace(self, name=self.name if name is None else name)
