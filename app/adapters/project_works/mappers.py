from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.adapters._typing import require_uuid
from app.domain.project_works import ProjectWork


def project_work_dict_to_entity(payload: dict[str, Any]) -> ProjectWork:
    return ProjectWork(
        project_work_id=require_uuid(payload["project_work_id"], "project_work_id"),
        project_work_name=payload.get("project_work_name"),
        project=require_uuid(payload["project"], "project"),
        work=require_uuid(payload["work"], "work"),
        quantity=Decimal(str(payload["quantity"])),
        summ=(
            Decimal(str(payload["summ"]))
            if payload.get("summ") is not None
            else None
        ),
        created_by=require_uuid(payload["created_by"], "created_by"),
        created_at=int(payload["created_at"]),
        signed=bool(payload.get("signed", False)),
    )


def project_work_entity_to_create_payload(
    project_work: ProjectWork,
) -> dict[str, Any]:
    return {
        "project_work_id": project_work.project_work_id,
        "project_work_name": project_work.project_work_name,
        "project": project_work.project,
        "work": project_work.work,
        "quantity": project_work.quantity,
        "summ": project_work.summ,
        "created_by": project_work.created_by,
        "created_at": project_work.created_at,
        "signed": project_work.signed,
    }


def project_work_entity_to_response(project_work: ProjectWork) -> dict[str, Any]:
    return {
        "project_work_id": str(project_work.project_work_id),
        "project_work_name": project_work.project_work_name,
        "project": str(project_work.project),
        "work": str(project_work.work),
        "quantity": float(project_work.quantity),
        "summ": float(project_work.summ) if project_work.summ is not None else None,
        "created_by": str(project_work.created_by),
        "created_at": project_work.created_at,
        "signed": project_work.signed,
    }
