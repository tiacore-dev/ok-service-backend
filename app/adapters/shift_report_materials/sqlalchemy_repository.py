from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.materials_manager import ShiftReportMaterialsManager
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

    def create_shift_report_material(
        self, shift_report_material: ShiftReportMaterial
    ) -> ShiftReportMaterial:
        created = self.manager.add(
            **shift_report_material_entity_to_create_payload(shift_report_material)
        )
        record = normalize_result(created)
        if record is None:
            raise ValueError("Shift report material creation did not return a record")
        return shift_report_material_dict_to_entity(record)

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
        return shift_report_material_dict_to_entity(record)

    def delete_shift_report_material(self, shift_report_material_id: UUID) -> bool:
        deleted = self.manager.delete(shift_report_material_id)
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
