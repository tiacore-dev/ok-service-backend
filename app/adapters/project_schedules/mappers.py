from __future__ import annotations

from typing import Any

from app.adapters._typing import require_uuid
from app.domain.project_schedules import ProjectSchedule


def project_schedule_dict_to_entity(payload: dict[str, Any]) -> ProjectSchedule:
    quantity = payload.get("quantity", 0)
    return ProjectSchedule(
        project_schedule_id=require_uuid(payload["project_schedule_id"], "project_schedule_id"),
        project=require_uuid(payload["project"], "project"),
        work=require_uuid(payload["work"], "work"),
        quantity=float(quantity),
        created_by=require_uuid(payload["created_by"], "created_by"),
        created_at=int(payload["created_at"]),
        date=payload.get("date"),
    )


def project_schedule_entity_to_create_payload(schedule: ProjectSchedule) -> dict[str, Any]:
    return {
        "project_schedule_id": schedule.project_schedule_id,
        "project": schedule.project,
        "work": schedule.work,
        "quantity": schedule.quantity,
        "created_by": schedule.created_by,
        "created_at": schedule.created_at,
        "date": schedule.date,
    }


def project_schedule_entity_to_response(schedule: ProjectSchedule) -> dict[str, Any]:
    return {
        "project_schedule_id": str(schedule.project_schedule_id),
        "project": str(schedule.project),
        "work": str(schedule.work),
        "quantity": schedule.quantity,
        "created_by": str(schedule.created_by),
        "created_at": schedule.created_at,
        "date": schedule.date,
    }
