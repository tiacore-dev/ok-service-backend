from __future__ import annotations

from typing import Any

from app.adapters._typing import require_uuid, to_uuid
from app.domain.leaves import AbsenceReason, Leave


def leave_dict_to_entity(payload: dict[str, Any]) -> Leave:
    return Leave(
        leave_id=require_uuid(payload["leave_id"], "leave_id"),
        start_date=int(payload["start_date"]),
        end_date=int(payload["end_date"]),
        reason=AbsenceReason(payload["reason"]),
        user_id=require_uuid(
            payload["user"] if "user" in payload else payload["user_id"],
            "user_id",
        ),
        responsible_id=require_uuid(
            payload["responsible"]
            if "responsible" in payload
            else payload["responsible_id"],
            "responsible_id",
        ),
        comment=payload.get("comment"),
        created_by=require_uuid(payload["created_by"], "created_by"),
        created_at=int(payload["created_at"]),
        updated_by=to_uuid(payload.get("updated_by")),
        updated_at=payload.get("updated_at"),
        deleted=bool(payload.get("deleted", False)),
    )


def leave_entity_to_create_payload(leave: Leave) -> dict[str, Any]:
    return {
        "start_date": leave.start_date,
        "end_date": leave.end_date,
        "reason": leave.reason,
        "user_id": leave.user_id,
        "responsible_id": leave.responsible_id,
        "comment": leave.comment,
        "created_by": leave.created_by,
        "created_at": leave.created_at,
        "updated_by": leave.updated_by,
        "updated_at": leave.updated_at,
        "deleted": leave.deleted,
    }


def leave_entity_to_response(leave: Leave) -> dict[str, Any]:
    return {
        "leave_id": str(leave.leave_id),
        "start_date": leave.start_date,
        "end_date": leave.end_date,
        "reason": leave.reason.value,
        "user": str(leave.user_id),
        "responsible": str(leave.responsible_id),
        "comment": leave.comment,
        "created_by": str(leave.created_by),
        "created_at": leave.created_at,
        "updated_by": str(leave.updated_by) if leave.updated_by else None,
        "updated_at": leave.updated_at,
        "deleted": leave.deleted,
    }


def leave_entity_to_list_item(leave: Leave) -> dict[str, Any]:
    return leave_entity_to_response(leave)
