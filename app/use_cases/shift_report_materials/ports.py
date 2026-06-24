from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.shift_report_materials import ShiftReportMaterial

from .dto import ShiftReportMaterialListQuery


class ShiftReportMaterialRepository(Protocol):
    def create_shift_report_material(
        self, shift_report_material: ShiftReportMaterial
    ) -> ShiftReportMaterial: ...

    def get_shift_report_material(
        self, shift_report_material_id: UUID
    ) -> ShiftReportMaterial | None: ...

    def update_shift_report_material(
        self, shift_report_material: ShiftReportMaterial
    ) -> ShiftReportMaterial | None: ...

    def delete_shift_report_material(self, shift_report_material_id: UUID) -> bool: ...

    def list_shift_report_materials(
        self, query: ShiftReportMaterialListQuery
    ) -> list[ShiftReportMaterial]: ...
