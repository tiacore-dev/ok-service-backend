from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.adapters._typing import require_uuid, to_uuid
from app.domain.work_prices import WorkPrice


def work_price_dict_to_entity(payload: dict[str, Any]) -> WorkPrice:
    return WorkPrice(
        work_price_id=require_uuid(payload["work_price_id"], "work_price_id"),
        work=require_uuid(payload["work"], "work"),
        category=int(payload["category"]),
        price=Decimal(str(payload["price"])),
        created_by=require_uuid(payload["created_by"], "created_by"),
        created_at=int(payload["created_at"]),
        deleted=bool(payload.get("deleted", False)),
    )


def work_price_entity_to_create_payload(work_price: WorkPrice) -> dict[str, Any]:
    return {
        "work_price_id": work_price.work_price_id,
        "work": work_price.work,
        "category": work_price.category,
        "price": work_price.price,
        "created_by": work_price.created_by,
        "created_at": work_price.created_at,
        "deleted": work_price.deleted,
    }


def work_price_entity_to_response(work_price: WorkPrice) -> dict[str, Any]:
    return {
        "work_price_id": str(work_price.work_price_id),
        "work": str(work_price.work),
        "category": work_price.category,
        "price": float(work_price.price),
        "created_by": str(work_price.created_by),
        "created_at": work_price.created_at,
        "deleted": work_price.deleted,
    }

