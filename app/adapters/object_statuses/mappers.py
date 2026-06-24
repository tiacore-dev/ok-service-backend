from __future__ import annotations

from typing import Any

from app.domain.object_statuses import ObjectStatus


def object_status_dict_to_entity(payload: dict[str, Any]) -> ObjectStatus:
    return ObjectStatus(
        object_status_id=payload["object_status_id"],
        name=str(payload["name"]),
    )


def object_status_entity_to_response(status: ObjectStatus) -> dict[str, Any]:
    return {
        "object_status_id": str(status.object_status_id),
        "name": status.name,
    }
