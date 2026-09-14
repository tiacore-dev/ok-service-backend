from __future__ import annotations

from typing import Any

from app.adapters._typing import require_uuid, to_uuid
from app.domain.projects import Project, ProjectStatus


def project_dict_to_entity(payload: dict[str, Any]) -> Project:
    raw_status = payload.get("status")
    status = (
        ProjectStatus.PENDING
        if "status" not in payload or raw_status is None
        else ProjectStatus(raw_status)
    )
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
        status=status,
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
        "status": project.status.value,
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
        "status": project.status.value,
    }


def project_dict_to_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Serialize a stored project without applying write-time validation.

    Project creation and updates use the strict domain entity. Reads must keep
    historical rows available even when they no longer satisfy that entity's
    invariants, for example when ``name`` is empty.
    """
    return {
        "project_id": (
            str(payload["project_id"])
            if payload.get("project_id") is not None
            else None
        ),
        "name": payload.get("name"),
        "object": str(payload["object"]) if payload.get("object") is not None else None,
        "project_leader": (
            str(payload["project_leader"])
            if payload.get("project_leader") is not None
            else None
        ),
        "night_shift_available": payload.get("night_shift_available"),
        "extreme_conditions_available": payload.get("extreme_conditions_available"),
        "created_at": payload.get("created_at"),
        "created_by": (
            str(payload["created_by"])
            if payload.get("created_by") is not None
            else None
        ),
        "deleted": payload.get("deleted"),
        "status": payload.get("status", ProjectStatus.PENDING.value),
    }
