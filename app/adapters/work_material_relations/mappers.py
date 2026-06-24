from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.adapters._typing import require_uuid
from app.domain.work_material_relations import WorkMaterialRelation


def work_material_relation_dict_to_entity(
    payload: dict[str, Any],
) -> WorkMaterialRelation:
    return WorkMaterialRelation(
        work_material_relation_id=require_uuid(
            payload["work_material_relation_id"], "work_material_relation_id"
        ),
        work=require_uuid(payload["work"], "work"),
        material=require_uuid(payload["material"], "material"),
        quantity=Decimal(str(payload["quantity"])),
        created_by=require_uuid(payload["created_by"], "created_by"),
        created_at=int(payload["created_at"]),
    )


def work_material_relation_entity_to_create_payload(
    work_material_relation: WorkMaterialRelation,
) -> dict[str, Any]:
    return {
        "work_material_relation_id": work_material_relation.work_material_relation_id,
        "work": work_material_relation.work,
        "material": work_material_relation.material,
        "quantity": work_material_relation.quantity,
        "created_by": work_material_relation.created_by,
        "created_at": work_material_relation.created_at,
    }


def work_material_relation_entity_to_response(
    work_material_relation: WorkMaterialRelation,
) -> dict[str, Any]:
    return {
        "work_material_relation_id": str(work_material_relation.work_material_relation_id),
        "work": str(work_material_relation.work),
        "material": str(work_material_relation.material),
        "quantity": float(work_material_relation.quantity),
        "created_by": str(work_material_relation.created_by),
        "created_at": work_material_relation.created_at,
    }
