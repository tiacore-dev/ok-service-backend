from __future__ import annotations

from typing import Any

from app.adapters._typing import require_uuid
from app.domain.materials import Material


def material_dict_to_entity(payload: dict[str, Any]) -> Material:
    return Material(
        material_id=require_uuid(payload["material_id"], "material_id"),
        name=str(payload["name"]),
        measurement_unit=payload.get("measurement_unit"),
        created_by=require_uuid(payload["created_by"], "created_by"),
        created_at=int(payload["created_at"]),
        deleted=bool(payload["deleted"]),
    )


def material_entity_to_create_payload(material: Material) -> dict[str, Any]:
    return {
        "material_id": material.material_id,
        "name": material.name,
        "measurement_unit": material.measurement_unit,
        "created_by": material.created_by,
        "created_at": material.created_at,
        "deleted": material.deleted,
    }


def material_entity_to_response(material: Material) -> dict[str, Any]:
    return {
        "material_id": str(material.material_id),
        "name": material.name,
        "measurement_unit": material.measurement_unit,
        "created_by": str(material.created_by),
        "created_at": material.created_at,
        "deleted": material.deleted,
    }
