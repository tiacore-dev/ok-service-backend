from __future__ import annotations

from typing import Any

from app.adapters._typing import require_uuid, to_uuid
from app.domain.objects import Object


def object_dict_to_entity(payload: dict[str, Any]) -> Object:
    return Object(
        object_id=require_uuid(payload["object_id"], "object_id"),
        name=str(payload["name"]),
        address=payload.get("address"),
        description=payload.get("description"),
        city_id=to_uuid(payload.get("city")),
        status=payload.get("status"),
        manager=to_uuid(payload.get("manager")),
        lng=payload.get("lng"),
        ltd=payload.get("ltd"),
        created_by=to_uuid(payload.get("created_by")),
        created_at=int(payload["created_at"]),
        deleted=bool(payload.get("deleted", False)),
    )


def object_entity_to_create_payload(obj: Object) -> dict[str, Any]:
    return {
        "object_id": obj.object_id,
        "name": obj.name,
        "address": obj.address,
        "description": obj.description,
        "city_id": obj.city_id,
        "status": obj.status,
        "manager": obj.manager,
        "lng": obj.lng,
        "ltd": obj.ltd,
        "created_by": obj.created_by,
        "created_at": obj.created_at,
        "deleted": obj.deleted,
    }


def object_entity_to_response(obj: Object) -> dict[str, Any]:
    return {
        "object_id": str(obj.object_id),
        "name": obj.name,
        "address": obj.address,
        "description": obj.description,
        "city": str(obj.city_id) if obj.city_id else None,
        "status": obj.status,
        "manager": str(obj.manager) if obj.manager else None,
        "lng": obj.lng,
        "ltd": obj.ltd,
        "created_at": obj.created_at,
        "created_by": str(obj.created_by) if obj.created_by else None,
        "deleted": obj.deleted,
    }
