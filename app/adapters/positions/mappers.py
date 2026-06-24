from __future__ import annotations

from typing import Any

from app.adapters._typing import require_uuid, to_uuid
from app.domain.positions import Position


def position_dict_to_entity(payload: dict[str, Any]) -> Position:
    return Position(
        position_id=require_uuid(payload["position_id"], "position_id"),
        name=str(payload["name"]),
        created_by=to_uuid(payload.get("created_by")),
        created_at=int(payload["created_at"]),
    )


def position_entity_to_create_payload(position: Position) -> dict[str, Any]:
    return {
        "position_id": position.position_id,
        "name": position.name,
        "created_by": position.created_by,
        "created_at": position.created_at,
    }


def position_entity_to_response(position: Position) -> dict[str, Any]:
    return {
        "position_id": str(position.position_id),
        "name": position.name,
        "created_by": str(position.created_by) if position.created_by else None,
        "created_at": position.created_at,
    }
