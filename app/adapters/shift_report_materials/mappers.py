from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.adapters._typing import require_uuid, to_uuid
from app.domain.shift_report_materials import ShiftReportMaterial


def shift_report_material_dict_to_entity(
    payload: dict[str, Any],
) -> ShiftReportMaterial:
    return ShiftReportMaterial(
        shift_report_material_id=require_uuid(
            payload["shift_report_material_id"], "shift_report_material_id"
        ),
        shift_report=require_uuid(payload["shift_report"], "shift_report"),
        material=require_uuid(payload["material"], "material"),
        quantity=Decimal(str(payload["quantity"])),
        created_by=require_uuid(payload["created_by"], "created_by"),
        created_at=int(payload["created_at"]),
        shift_report_detail=to_uuid(payload.get("shift_report_detail")),
    )


def shift_report_material_entity_to_create_payload(
    shift_report_material: ShiftReportMaterial,
) -> dict[str, Any]:
    return {
        "shift_report_material_id": shift_report_material.shift_report_material_id,
        "shift_report": shift_report_material.shift_report,
        "material": shift_report_material.material,
        "quantity": shift_report_material.quantity,
        "created_by": shift_report_material.created_by,
        "created_at": shift_report_material.created_at,
        "shift_report_detail": shift_report_material.shift_report_detail,
    }


def shift_report_material_entity_to_response(
    shift_report_material: ShiftReportMaterial,
) -> dict[str, Any]:
    return {
        "shift_report_material_id": str(shift_report_material.shift_report_material_id),
        "shift_report": str(shift_report_material.shift_report),
        "material": str(shift_report_material.material),
        "quantity": float(shift_report_material.quantity),
        "shift_report_detail": (
            str(shift_report_material.shift_report_detail)
            if shift_report_material.shift_report_detail
            else None
        ),
        "created_by": str(shift_report_material.created_by),
        "created_at": shift_report_material.created_at,
    }
