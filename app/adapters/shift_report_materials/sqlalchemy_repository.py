from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.adapters.statistics import ProjectMaterialStatistics
from app.database.managers.materials_manager import ShiftReportMaterialsManager
from app.database.managers.projects_managers import ProjectsManager
from app.database.managers.shift_reports_managers import ShiftReportsManager
from app.domain.shift_report_materials import ShiftReportMaterial
from app.use_cases.shift_report_materials.dto import ShiftReportMaterialListQuery
from app.use_cases.shift_report_materials.ports import ShiftReportMaterialRepository

from .mappers import (
    shift_report_material_dict_to_entity,
    shift_report_material_entity_to_create_payload,
)


@dataclass(slots=True)
class SQLAlchemyShiftReportMaterialRepository(ShiftReportMaterialRepository):
    manager: ShiftReportMaterialsManager = field(
        default_factory=ShiftReportMaterialsManager
    )
    reports_manager: ShiftReportsManager = field(default_factory=ShiftReportsManager)
    projects_manager: ProjectsManager = field(default_factory=ProjectsManager)
    statistics: ProjectMaterialStatistics | None = None

    def _project_id_for_report(self, shift_report_id: UUID) -> UUID | None:
        report = normalize_result(self.reports_manager.get_by_id(shift_report_id))
        if report is None:
            return None
        return UUID(str(report["project"]))

    def _recalculate(self, *project_ids: UUID | None) -> None:
        if self.statistics is not None:
            self.statistics.recalculate_many(
                {project_id for project_id in project_ids if project_id is not None}
            )

    def create_shift_report_material(
        self, shift_report_material: ShiftReportMaterial
    ) -> ShiftReportMaterial:
        created = self.manager.add(
            **shift_report_material_entity_to_create_payload(shift_report_material)
        )
        record = normalize_result(created)
        if record is None:
            raise ValueError("Shift report material creation did not return a record")
        entity = shift_report_material_dict_to_entity(record)
        self._recalculate(self._project_id_for_report(entity.shift_report))
        return entity

    def get_shift_report_material(
        self, shift_report_material_id: UUID
    ) -> ShiftReportMaterial | None:
        record = normalize_result(self.manager.get_by_id(shift_report_material_id))
        if record is None:
            return None
        return shift_report_material_dict_to_entity(record)

    def update_shift_report_material(
        self, shift_report_material: ShiftReportMaterial
    ) -> ShiftReportMaterial | None:
        current = self.get_shift_report_material(
            shift_report_material.shift_report_material_id
        )
        updated = self.manager.update(
            record_id=shift_report_material.shift_report_material_id,
            shift_report=shift_report_material.shift_report,
            material=shift_report_material.material,
            quantity=shift_report_material.quantity,
            shift_report_detail=shift_report_material.shift_report_detail,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        entity = shift_report_material_dict_to_entity(record)
        self._recalculate(
            self._project_id_for_report(current.shift_report) if current else None,
            self._project_id_for_report(entity.shift_report),
        )
        return entity

    def delete_shift_report_material(self, shift_report_material_id: UUID) -> bool:
        current = self.get_shift_report_material(shift_report_material_id)
        deleted = self.manager.delete(shift_report_material_id)
        if deleted is not None and current is not None:
            self._recalculate(self._project_id_for_report(current.shift_report))
        return deleted is not None

    def list_shift_report_materials(
        self, query: ShiftReportMaterialListQuery
    ) -> list[ShiftReportMaterial]:
        records = self.manager.get_all_filtered(
            offset=query.offset,
            limit=query.limit,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            shift_report=query.shift_report,
            material=query.material,
            shift_report_detail=query.shift_report_detail,
            created_by=query.created_by,
            created_at=query.created_at,
        )
        return [shift_report_material_dict_to_entity(record) for record in records]

    def get_shift_report_context(
        self, shift_report_id: UUID
    ) -> tuple[UUID, UUID | None, bool] | None:
        report = normalize_result(self.reports_manager.get_by_id(shift_report_id))
        if report is None:
            return None
        project_id = UUID(str(report["project"]))
        project = normalize_result(self.projects_manager.get_by_id(project_id))
        project_leader = (
            UUID(str(project["project_leader"]))
            if project and project.get("project_leader")
            else None
        )
        return project_id, project_leader, bool(report.get("signed", False))
