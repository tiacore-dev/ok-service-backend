from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.adapters._typing import require_uuid
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


def work_price_dict_to_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Serialize a stored row without validating legacy nullable columns.

    Work-price writes are validated by the input schema and domain entity. Reads
    must remain available for historical rows created before those constraints
    were enforced, so missing category/price values are returned as null.
    """
    price = payload.get("price")
    return {
        "work_price_id": str(payload["work_price_id"]),
        "work": str(payload["work"]) if payload.get("work") is not None else None,
        "category": payload.get("category"),
        "price": float(price) if price is not None else None,
        "created_by": (
            str(payload["created_by"])
            if payload.get("created_by") is not None
            else None
        ),
        "created_at": payload.get("created_at"),
        "deleted": payload.get("deleted", False),
    }
