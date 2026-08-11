from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.places import Place, PlaceForbiddenError, PlaceNotFoundError
from app.use_cases.places.dto import (
    CreatePlaceCommand,
    PlaceActor,
    PlaceRepository,
    UpdatePlaceCommand,
)


def _require_admin(actor: PlaceActor) -> None:
    if actor.role != "admin":
        raise PlaceForbiddenError("Forbidden")


@dataclass(slots=True)
class CreatePlaceUseCase:
    repository: PlaceRepository

    def execute(self, command: CreatePlaceCommand, actor: PlaceActor) -> Place:
        _require_admin(actor)
        place = Place(uuid4(), command.object_id, command.name, command.description)
        place.validate_for_write()
        return self.repository.create_place(place)


@dataclass(slots=True)
class GetPlaceUseCase:
    repository: PlaceRepository

    def execute(self, place_id: UUID) -> Place:
        place = self.repository.get_place(place_id)
        if place is None:
            raise PlaceNotFoundError("Place not found")
        return place


@dataclass(slots=True)
class ListPlacesUseCase:
    repository: PlaceRepository

    def execute(self) -> list[Place]:
        return self.repository.list_places()


@dataclass(slots=True)
class UpdatePlaceUseCase:
    repository: PlaceRepository

    def execute(self, command: UpdatePlaceCommand, actor: PlaceActor) -> Place:
        _require_admin(actor)
        current = self.repository.get_place(command.place_id)
        if current is None:
            raise PlaceNotFoundError("Place not found")
        updated = current.with_updates(
            object_id=command.object_id,
            name=command.name,
            description=command.description,
            deleted=command.deleted,
        )
        updated.validate_for_write()
        result = self.repository.update_place(updated)
        if result is None:
            raise PlaceNotFoundError("Place not found")
        return result


@dataclass(slots=True)
class SoftDeletePlaceUseCase:
    repository: PlaceRepository

    def execute(self, place_id: UUID, actor: PlaceActor) -> Place:
        _require_admin(actor)
        current = self.repository.get_place(place_id)
        if current is None:
            raise PlaceNotFoundError("Place not found")
        updated = current.with_updates(deleted=True)
        result = self.repository.update_place(updated)
        if result is None:
            raise PlaceNotFoundError("Place not found")
        return result


@dataclass(slots=True)
class HardDeletePlaceUseCase:
    repository: PlaceRepository

    def execute(self, place_id: UUID, actor: PlaceActor) -> None:
        _require_admin(actor)
        if self.repository.get_place(place_id) is None:
            raise PlaceNotFoundError("Place not found")
        if not self.repository.delete_place(place_id):
            raise PlaceNotFoundError("Place not found")
