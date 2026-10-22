"""Queries shared by manual and automatic shift-material writes."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.database.models import ProjectMaterials, ShiftReportDetails, ShiftReports
from app.domain.shift_report_materials import ShiftReportMaterialValidationError
from app.domain.shift_report_materials.policies import (
    normalize_material_quantity,
    validate_shift_material_links,
)


def find_project_material_id(
    session: Session,
    shift_report_id: UUID,
    material_id: UUID,
    detail_id: UUID | None,
) -> UUID | None:
    if detail_id is None:
        return None
    row = (
        session.query(ProjectMaterials.project_material_id)
        .join(ShiftReports, ShiftReports.project == ProjectMaterials.project)
        .join(
            ShiftReportDetails,
            (ShiftReportDetails.shift_report == ShiftReports.shift_report_id)
            & (ShiftReportDetails.project_work == ProjectMaterials.project_work),
        )
        .filter(
            ShiftReports.shift_report_id == shift_report_id,
            ShiftReportDetails.shift_report_detail_id == detail_id,
            ProjectMaterials.material == material_id,
        )
        .order_by(ProjectMaterials.created_at, ProjectMaterials.project_material_id)
        .with_for_update(of=ProjectMaterials, read=True, key_share=True)
        .first()
    )
    return row[0] if row is not None else None


def validate_shift_material_record(session, record) -> None:
    with session.no_autoflush:
        material = (
            session.query(ProjectMaterials)
            .filter(ProjectMaterials.project_material_id == record.project_material)
            .with_for_update(of=ProjectMaterials, read=True, key_share=True)
            .first()
        )
        report = session.get(ShiftReports, record.shift_report)
        if material is None or report is None:
            raise ShiftReportMaterialValidationError(
                "Project material or shift report does not exist"
            )
        detail = (
            session.get(ShiftReportDetails, record.shift_report_detail)
            if record.shift_report_detail
            else None
        )
        if record.shift_report_detail is not None and detail is None:
            raise ShiftReportMaterialValidationError(
                "Shift report detail does not exist"
            )
        validate_shift_material_links(
            shift_project=report.project,
            material_project=material.project,
            shift_report=record.shift_report,
            detail_report=detail.shift_report if detail else None,
            material_work=material.project_work,
            detail_work=detail.project_work if detail else None,
        )
        unit = material.materials.measurement_unit_ref if material.materials else None
        record.quantity = normalize_material_quantity(
            record.quantity, unit.name if unit else None
        )
