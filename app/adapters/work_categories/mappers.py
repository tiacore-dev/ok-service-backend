from __future__ import annotations

from typing import Any

from app.adapters._typing import require_uuid
from app.domain.work_categories import WorkCategory


def work_category_dict_to_entity(payload: dict[str, Any]) -> WorkCategory:
    return WorkCategory(
        work_category_id=require_uuid(payload["work_category_id"], "work_category_id"),
        name=str(payload["name"]),
        created_by=require_uuid(payload["created_by"], "created_by"),
        created_at=int(payload["created_at"]),
        deleted=bool(payload.get("deleted", False)),
    )


def work_category_entity_to_create_payload(
    work_category: WorkCategory,
) -> dict[str, Any]:
    return {
        "work_category_id": work_category.work_category_id,
        "name": work_category.name,
        "created_by": work_category.created_by,
        "created_at": work_category.created_at,
        "deleted": work_category.deleted,
    }


def work_category_entity_to_response(work_category: WorkCategory) -> dict[str, Any]:
    return {
        "work_category_id": str(work_category.work_category_id),
        "name": work_category.name,
        "created_by": str(work_category.created_by),
        "created_at": work_category.created_at,
        "deleted": work_category.deleted,
    }
