from .repository import SQLAlchemyPlaceRepository
from app.domain.places import Place


def place_entity_to_response(place: Place) -> dict[str, object]:
    return {
        "place_id": str(place.place_id),
        "object_id": str(place.object_id),
        "name": place.name,
        "description": place.description,
        "deleted": place.deleted,
    }

__all__ = ["SQLAlchemyPlaceRepository", "place_entity_to_response"]
