from __future__ import annotations

from typing import Any

from app.adapters._typing import require_uuid, to_uuid
from app.domain.projects import Project


def project_dict_to_entity(payload: dict[str, Any]) -> Project:
    return Project(
        project_id=require_uuid(payload["project_id"], "project_id"),
        name=str(payload["name"]),
        object=require_uuid(payload["object"], "object"),
        project_leader=to_uuid(payload.get("project_leader")),
        night_shift_available=bool(payload.get("night_shift_available", False)),
        extreme_conditions_available=bool(
            payload.get("extreme_conditions_available", False)
        ),
        created_by=to_uuid(payload.get("created_by")),
        created_at=int(payload["created_at"]),
        deleted=bool(payload.get("deleted", False)),
    )


def project_entity_to_create_payload(project: Project) -> dict[str, Any]:
    return {
        "project_id": project.project_id,
        "name": project.name,
        "object": project.object,
        "project_leader": project.project_leader,
        "night_shift_available": project.night_shift_available,
        "extreme_conditions_available": project.extreme_conditions_available,
        "created_by": project.created_by,
        "created_at": project.created_at,
        "deleted": project.deleted,
    }


def project_entity_to_response(project: Project) -> dict[str, Any]:
    return {
        "project_id": str(project.project_id),
        "name": project.name,
        "object": str(project.object),
        "project_leader": (
            str(project.project_leader) if project.project_leader else None
        ),
        "night_shift_available": project.night_shift_available,
        "extreme_conditions_available": project.extreme_conditions_available,
        "created_at": project.created_at,
        "created_by": str(project.created_by) if project.created_by else None,
        "deleted": project.deleted,
    }
