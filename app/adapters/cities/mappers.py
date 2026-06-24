from __future__ import annotations

from typing import Any

from app.adapters._typing import require_uuid, to_uuid
from app.domain.cities import City


def city_dict_to_entity(payload: dict[str, Any]) -> City:
    return City(
        city_id=require_uuid(payload["city_id"], "city_id"),
        name=str(payload["name"]),
        created_by=to_uuid(payload.get("created_by")),
        created_at=int(payload["created_at"]),
        deleted=bool(payload.get("deleted", False)),
    )


def city_entity_to_create_payload(city: City) -> dict[str, Any]:
    return {
        "city_id": city.city_id,
        "name": city.name,
        "created_by": city.created_by,
        "created_at": city.created_at,
        "deleted": city.deleted,
    }


def city_entity_to_response(city: City) -> dict[str, Any]:
    return {
        "city_id": str(city.city_id),
        "name": city.name,
        "created_by": str(city.created_by) if city.created_by else None,
        "created_at": city.created_at,
        "deleted": city.deleted,
    }
