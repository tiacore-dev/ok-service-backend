from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from .errors import CityValidationError


@dataclass(frozen=True, slots=True)
class City:
    city_id: UUID
    name: str
    created_by: UUID | None
    created_at: int
    deleted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "created_at", int(self.created_at))
        object.__setattr__(self, "deleted", bool(self.deleted))
        if not self.name:
            raise CityValidationError("City name is required.")

    def with_updates(
        self,
        *,
        name: str | None = None,
        deleted: bool | None = None,
    ) -> "City":
        return replace(
            self,
            name=self.name if name is None else name,
            deleted=self.deleted if deleted is None else deleted,
        )
