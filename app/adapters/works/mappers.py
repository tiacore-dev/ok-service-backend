from __future__ import annotations

from typing import Any

from app.adapters._typing import require_uuid, to_uuid
from app.domain.works import Work


def _measurement_unit_id(value: Any):
    if isinstance(value, dict):
        return require_uuid(value.get("measurement_unit_id"), "measurement_unit_id")
    return value


def work_dict_to_entity(payload: dict[str, Any]) -> Work:
    return Work(
        work_id=require_uuid(payload["work_id"], "work_id"),
        name=str(payload["name"]),
        category=payload.get("category"),
        measurement_unit=payload.get("measurement_unit"),
        created_at=int(payload["created_at"]),
        created_by=require_uuid(payload["created_by"], "created_by"),
        deleted=bool(payload.get("deleted", False)),
        work_prices=list(payload.get("work_prices", [])),
    )


def work_entity_to_create_payload(work: Work) -> dict[str, Any]:
    category = work.category
    category_id = None
    if isinstance(category, dict):
        category_id = to_uuid(category.get("work_category_id"))
    return {
        "work_id": work.work_id,
        "name": work.name,
        "category": category_id,
        "measurement_unit": _measurement_unit_id(work.measurement_unit),
        "created_by": work.created_by,
        "created_at": work.created_at,
        "deleted": work.deleted,
    }


def work_entity_to_response(work: Work) -> dict[str, Any]:
    return {
        "work_id": str(work.work_id),
        "name": work.name,
        "category": work.category,
        "measurement_unit": work.measurement_unit,
        "created_at": work.created_at,
        "created_by": str(work.created_by),
        "deleted": work.deleted,
        "work_prices": work.work_prices,
    }
