from dataclasses import dataclass, replace
from uuid import UUID

from .errors import PlaceValidationError


@dataclass(frozen=True, slots=True)
class Place:
    place_id: UUID
    object_id: UUID
    name: str | None
    description: str | None
    deleted: bool = False

    def validate_for_write(self) -> None:
        if self.name is None or not self.name.strip():
            raise PlaceValidationError("Place name is required.")

    def with_updates(
        self,
        *,
        object_id: UUID | None = None,
        name: str | None = None,
        description: str | None = None,
        deleted: bool | None = None,
    ) -> "Place":
        return replace(
            self,
            object_id=self.object_id if object_id is None else object_id,
            name=self.name if name is None else name,
            description=self.description if description is None else description,
            deleted=self.deleted if deleted is None else deleted,
        )
