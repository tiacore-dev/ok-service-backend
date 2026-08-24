from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.adapters.places.repository import _entity
from app.domain.places import (
    Place,
    PlaceConflictError,
    PlaceForbiddenError,
    PlaceValidationError,
)
from app.use_cases.places import (
    CreatePlaceCommand,
    CreatePlaceUseCase,
    HardDeletePlaceUseCase,
    ListPlacesForObjectUseCase,
    PlaceActor,
    SoftDeletePlaceUseCase,
    UpdatePlaceCommand,
    UpdatePlaceUseCase,
)
from app.use_cases.places.dto import PlaceRepository
from app.web.places.routes import _error


class FakePlaceRepository(PlaceRepository):
    def __init__(self, place: Place | None = None):
        self.place: Place | None = place
        self.created: Place | None = None
        self.updated: Place | None = None
        self.deleted: UUID | None = None
        self.listed_object_id: UUID | None = None
        self.relations_exist = False

    def create_place(self, place: Place) -> Place:
        self.created = place
        self.place = place
        return place

    def get_place(self, place_id: UUID) -> Place | None:
        return self.place if self.place and self.place.place_id == place_id else None

    def update_place(self, place: Place) -> Place | None:
        self.updated = place
        self.place = place
        return place

    def delete_place(self, place_id: UUID) -> bool:
        self.deleted = place_id
        return self.place is not None and self.place.place_id == place_id

    def has_relations(self, place_id: UUID) -> bool:
        return self.relations_exist

    def list_places(self) -> list[Place]:
        return [self.place] if self.place else []

    def list_places_by_object(self, object_id: UUID) -> list[Place]:
        self.listed_object_id = object_id
        return [self.place] if self.place and self.place.object_id == object_id else []


def _place(name: str = "Main hall") -> Place:
    return Place(uuid4(), uuid4(), name, "Description", False)


def test_create_place_requires_admin_and_name():
    repository = FakePlaceRepository()
    actor = PlaceActor(role="admin")
    result = CreatePlaceUseCase(repository).execute(
        CreatePlaceCommand(uuid4(), "  Main hall  ", None), actor
    )
    assert result.name == "  Main hall  "
    assert repository.created is not None
    assert repository.created.object_id == result.object_id

    with pytest.raises(PlaceForbiddenError):
        CreatePlaceUseCase(FakePlaceRepository()).execute(
            CreatePlaceCommand(uuid4(), "Main hall"), PlaceActor(role="user")
        )

    with pytest.raises(PlaceValidationError):
        CreatePlaceUseCase(FakePlaceRepository()).execute(
            CreatePlaceCommand(uuid4(), "   "), actor
        )


def test_update_and_delete_places_are_admin_only():
    place = _place()
    repository = FakePlaceRepository(place)
    actor = PlaceActor(role="admin")

    updated = UpdatePlaceUseCase(repository).execute(
        UpdatePlaceCommand(place.place_id, name="Updated"), actor
    )
    assert updated.name == "Updated"

    deleted = SoftDeletePlaceUseCase(repository).execute(place.place_id, actor)
    assert deleted.deleted is True

    HardDeletePlaceUseCase(repository).execute(place.place_id, actor)
    assert repository.deleted == place.place_id

    with pytest.raises(PlaceForbiddenError):
        UpdatePlaceUseCase(FakePlaceRepository(place)).execute(
            UpdatePlaceCommand(place.place_id, name="Nope"), PlaceActor(role="user")
        )


def test_soft_delete_place_rejects_existing_relations():
    place = _place()
    repository = FakePlaceRepository(place)
    repository.relations_exist = True

    with pytest.raises(PlaceConflictError, match="used by a project or shift"):
        SoftDeletePlaceUseCase(repository).execute(place.place_id, PlaceActor(role="admin"))


def test_place_hard_delete_integrity_error_maps_to_conflict():
    response, status = _error(IntegrityError("fk", {}, Exception("dependent data")))

    assert status == 409
    assert response == {"msg": "Cannot delete place: dependent data exists."}


def test_update_rejects_empty_name_when_name_is_changed():
    place = _place()
    with pytest.raises(PlaceValidationError):
        UpdatePlaceUseCase(FakePlaceRepository(place)).execute(
            UpdatePlaceCommand(place.place_id, name="   "), PlaceActor(role="admin")
        )


def test_list_places_for_object_delegates_object_id():
    place = _place()
    repository = FakePlaceRepository(place)

    result = ListPlacesForObjectUseCase(repository).execute(place.object_id)

    assert result == [place]
    assert repository.listed_object_id == place.object_id


def test_get_and_list_places_allow_user():
    place = _place()
    repository = FakePlaceRepository(place)
    actor = PlaceActor(role="user")

    from app.use_cases.places import GetPlaceUseCase, ListPlacesUseCase

    assert GetPlaceUseCase(repository).execute(place.place_id, actor) == place
    assert ListPlacesUseCase(repository).execute(actor) == [place]


def test_mapper_keeps_invalid_legacy_values_for_get():
    place = _entity(
        {
            "place_id": str(uuid4()),
            "object_id": str(uuid4()),
            "name": None,
            "description": None,
            "deleted": False,
        }
    )
    assert place.name is None
    assert place.description is None
    assert place.deleted is False
