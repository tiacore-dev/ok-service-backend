from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.adapters._typing import require_uuid, to_uuid
from app.domain.project_materials import ProjectMaterial


def project_material_dict_to_entity(payload: dict[str, Any]) -> ProjectMaterial:
    return ProjectMaterial(
        project_material_id=require_uuid(
            payload["project_material_id"], "project_material_id"
        ),
        project=require_uuid(payload["project"], "project"),
        material=require_uuid(payload["material"], "material"),
        quantity=Decimal(str(payload["quantity"])),
        created_by=require_uuid(payload["created_by"], "created_by"),
        created_at=int(payload["created_at"]),
        project_work=to_uuid(payload.get("project_work")),
    )


def project_material_entity_to_create_payload(
    project_material: ProjectMaterial,
) -> dict[str, Any]:
    return {
        "project_material_id": project_material.project_material_id,
        "project": project_material.project,
        "material": project_material.material,
        "quantity": project_material.quantity,
        "created_by": project_material.created_by,
        "created_at": project_material.created_at,
        "project_work": project_material.project_work,
    }


def project_material_entity_to_response(
    project_material: ProjectMaterial,
) -> dict[str, Any]:
    return {
        "project_material_id": str(project_material.project_material_id),
        "project": str(project_material.project),
        "material": str(project_material.material),
        "quantity": float(project_material.quantity),
        "project_work": (
            str(project_material.project_work) if project_material.project_work else None
        ),
        "created_by": str(project_material.created_by),
        "created_at": project_material.created_at,
    }
