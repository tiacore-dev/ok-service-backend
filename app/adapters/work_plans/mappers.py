from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.adapters._typing import require_uuid, to_uuid
from app.domain.work_plans import WorkPlan


def work_plan_dict_to_entity(payload: dict[str, Any]) -> WorkPlan:
    value = payload["date"]
    return WorkPlan(
        work_plan_id=require_uuid(payload["work_plan_id"], "work_plan_id"),
        user_id=to_uuid(payload.get("user_id")),
        date=value if isinstance(value, date) else date.fromisoformat(str(value)),
        summ=Decimal(str(payload["summ"])),
        description=payload.get("description"),
        deleted=bool(payload.get("deleted", False)),
    )


def work_plan_entity_to_create_payload(entity: WorkPlan) -> dict[str, Any]:
    return {
        "work_plan_id": entity.work_plan_id,
        "user_id": entity.user_id,
        "date": entity.date,
        "summ": entity.summ,
        "description": entity.description,
        "deleted": entity.deleted,
    }


def work_plan_entity_to_response(entity: WorkPlan) -> dict[str, Any]:
    return {
        "work_plan_id": str(entity.work_plan_id),
        "user_id": str(entity.user_id) if entity.user_id is not None else None,
        "date": entity.date.isoformat(),
        "summ": format(entity.summ, ".2f"),
        "description": entity.description,
        "deleted": entity.deleted,
    }
