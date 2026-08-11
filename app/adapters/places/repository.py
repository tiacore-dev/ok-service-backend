from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result, require_uuid
from app.database.managers.objects_managers import PlacesManager
from app.domain.places import Place
from app.use_cases.places.dto import PlaceRepository


def _entity(payload: Mapping[str, object]) -> Place:
    raw_name = payload.get("name")
    raw_description = payload.get("description")
    raw_deleted = payload.get("deleted", False)
    return Place(
        place_id=require_uuid(payload["place_id"], "place_id"),
        object_id=require_uuid(payload["object_id"], "object_id"),
        name=raw_name if isinstance(raw_name, str) else None,
        description=raw_description if isinstance(raw_description, str) else None,
        deleted=raw_deleted if isinstance(raw_deleted, bool) else False,
    )


@dataclass(slots=True)
class SQLAlchemyPlaceRepository(PlaceRepository):
    manager: PlacesManager = field(default_factory=PlacesManager)

    def create_place(self, place: Place) -> Place:
        record = self.manager.add(
            place_id=place.place_id,
            object_id=place.object_id,
            name=place.name,
            description=place.description,
            deleted=place.deleted,
        )
        normalized = normalize_result(record)
        if normalized is None:
            raise ValueError("Place creation did not return a record")
        return _entity(normalized)

    def get_place(self, place_id: UUID) -> Place | None:
        record = normalize_result(self.manager.get_by_id(place_id))
        return _entity(record) if record else None

    def update_place(self, place: Place) -> Place | None:
        record = self.manager.update(
            record_id=place.place_id,
            object_id=place.object_id,
            name=place.name,
            description=place.description,
            deleted=place.deleted,
        )
        normalized = normalize_result(record)
        return _entity(normalized) if normalized is not None else None

    def delete_place(self, place_id: UUID) -> bool:
        return self.manager.delete(place_id) is not None

    def list_places(self) -> list[Place]:
        records = self.manager.get_all(offset=0, limit=None)
        return [_entity(record) for record in records]

    def list_places_by_object(self, object_id: UUID) -> list[Place]:
        records = self.manager.get_all_filtered(
            offset=0,
            limit=None,
            sort_by=None,
            object_id=object_id,
        )
        return [_entity(record) for record in records]
