from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.places import Place


@dataclass(frozen=True, slots=True)
class PlaceActor:
    role: str


@dataclass(frozen=True, slots=True)
class CreatePlaceCommand:
    object_id: UUID
    name: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class UpdatePlaceCommand:
    place_id: UUID
    object_id: UUID | None = None
    name: str | None = None
    description: str | None = None
    deleted: bool | None = None


class PlaceRepository(Protocol):
    def create_place(self, place: Place) -> Place: ...
    def get_place(self, place_id: UUID) -> Place | None: ...
    def update_place(self, place: Place) -> Place | None: ...
    def delete_place(self, place_id: UUID) -> bool: ...
    def list_places(self) -> list[Place]: ...
