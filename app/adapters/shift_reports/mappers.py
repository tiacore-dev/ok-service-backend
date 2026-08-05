from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.shift_reports import ShiftReport, ShiftReportDetail


def _uuid_value(payload: dict[str, Any], key: str) -> UUID:
    value = payload[key]
    if isinstance(value, dict):
        value = (
            value.get("id")
            or value.get("shift_report_detail_id")
            or value.get("project_work_id")
        )
    return UUID(str(value))


def shift_report_dict_to_entity(payload: dict[str, Any]) -> ShiftReport:
    return ShiftReport(
        shift_report_id=UUID(str(payload["shift_report_id"])),
        user=UUID(str(payload["user"])),
        date=int(payload["date"]),
        date_start=(
            int(payload["date_start"])
            if payload.get("date_start") is not None
            else None
        ),
        date_end=(
            int(payload["date_end"]) if payload.get("date_end") is not None else None
        ),
        project=UUID(str(payload["project"])),
        lng_start=payload.get("lng_start"),
        ltd_start=payload.get("ltd_start"),
        lng_end=payload.get("lng_end"),
        ltd_end=payload.get("ltd_end"),
        distance_start=payload.get("distance_start"),
        distance_end=payload.get("distance_end"),
        signed=bool(payload.get("signed", False)),
        deleted=bool(payload.get("deleted", False)),
        leave_id=UUID(str(payload["leave_id"])) if payload.get("leave_id") else None,
        created_by=UUID(str(payload["created_by"])),
        created_at=int(payload["created_at"]),
        night_shift=bool(payload.get("night_shift", False)),
        extreme_conditions=bool(payload.get("extreme_conditions", False)),
        number=int(payload["number"]),
        comment=payload.get("comment"),
        signed_at=payload.get("signed_at"),
        signed_by=payload.get("signed_by"),
        updated_at=payload.get("updated_at"),
        updated_by=payload.get("updated_by"),
    )


def shift_report_detail_dict_to_entity(payload: dict[str, Any]) -> ShiftReportDetail:
    shift_report = payload["shift_report"]
    shift_report_user = None
    shift_report_date = None
    shift_report_project = None
    if isinstance(shift_report, dict):
        shift_report_user = shift_report.get("user_id")
        shift_report_date = shift_report.get("date")
        shift_report_project = shift_report.get("project")
        shift_report = shift_report.get("id") or shift_report.get("shift_report_id")
    project_work = payload.get("project_work")
    project_work_name = None
    if isinstance(project_work, dict):
        project_work_name = project_work.get("name")
        project_work = project_work.get("project_work_id")
    return ShiftReportDetail(
        shift_report_detail_id=_uuid_value(payload, "shift_report_detail_id"),
        shift_report=UUID(str(shift_report)),
        project_work=(UUID(str(project_work)) if project_work is not None else None),
        work=_uuid_value(payload, "work"),
        quantity=Decimal(str(payload["quantity"])),
        summ=Decimal(str(payload["summ"])),
        created_by=_uuid_value(payload, "created_by"),
        created_at=int(payload["created_at"]),
        shift_report_user=UUID(str(shift_report_user)) if shift_report_user else None,
        shift_report_date=int(shift_report_date)
        if shift_report_date is not None
        else None,
        project_work_name=project_work_name,
        shift_report_project=(
            UUID(str(shift_report_project)) if shift_report_project else None
        ),
    )


def shift_report_detail_entity_to_response(entity: ShiftReportDetail) -> dict[str, Any]:
    return {
        "shift_report_detail_id": str(entity.shift_report_detail_id),
        "shift_report": {
            "id": str(entity.shift_report),
            "user_id": str(entity.shift_report_user)
            if entity.shift_report_user
            else None,
            "date": entity.shift_report_date,
            "project": str(entity.shift_report_project)
            if entity.shift_report_project
            else None,
        },
        "project_work": (
            {
                "project_work_id": str(entity.project_work),
                "name": entity.project_work_name,
            }
            if entity.project_work
            else None
        ),
        "work": str(entity.work),
        "quantity": float(entity.quantity),
        "summ": float(entity.summ),
        "created_by": str(entity.created_by),
        "created_at": entity.created_at,
    }


def shift_report_entity_to_response(entity: ShiftReport) -> dict[str, Any]:
    return {
        "shift_report_id": str(entity.shift_report_id),
        "user": str(entity.user),
        "date": entity.date,
        "date_start": entity.date_start,
        "date_end": entity.date_end,
        "project": str(entity.project),
        "lng_start": entity.lng_start,
        "ltd_start": entity.ltd_start,
        "lng_end": entity.lng_end,
        "ltd_end": entity.ltd_end,
        "distance_start": entity.distance_start,
        "distance_end": entity.distance_end,
        "signed": entity.signed,
        "deleted": entity.deleted,
        "leave_id": str(entity.leave_id) if entity.leave_id else None,
        "created_by": str(entity.created_by),
        "created_at": entity.created_at,
        "night_shift": entity.night_shift,
        "extreme_conditions": entity.extreme_conditions,
        "number": entity.number,
        "comment": entity.comment,
        "signed_at": entity.signed_at,
        "signed_by": entity.signed_by,
        "updated_at": entity.updated_at,
        "updated_by": entity.updated_by,
    }
