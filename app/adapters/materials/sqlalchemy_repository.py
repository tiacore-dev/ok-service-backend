from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.materials_manager import MaterialsManager
from app.domain.materials import Material
from app.use_cases.materials.dto import MaterialListQuery
from app.use_cases.materials.ports import MaterialRepository

from .mappers import material_dict_to_entity, material_entity_to_create_payload


@dataclass(slots=True)
class SQLAlchemyMaterialRepository(MaterialRepository):
    manager: MaterialsManager = field(default_factory=MaterialsManager)

    def create_material(self, material: Material) -> Material:
        created = self.manager.add(**material_entity_to_create_payload(material))
        record = normalize_result(created)
        if record is None:
            raise ValueError("Material creation did not return a record")
        return material_dict_to_entity(record)

    def get_material(self, material_id: UUID) -> Material | None:
        record = normalize_result(self.manager.get_by_id(material_id))
        if record is None:
            return None
        return material_dict_to_entity(record)

    def update_material(self, material: Material) -> Material | None:
        updated = self.manager.update(
            record_id=material.material_id,
            name=material.name,
            measurement_unit=material_entity_to_create_payload(material)["measurement_unit"],
            deleted=material.deleted,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return material_dict_to_entity(record)

    def delete_material(self, material_id: UUID) -> bool:
        deleted = self.manager.delete(material_id)
        return deleted is not None

    def list_materials(self, query: MaterialListQuery) -> list[Material]:
        records = self.manager.get_all_filtered(
            offset=query.offset,
            limit=query.limit,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            name=query.name,
            measurement_unit=query.measurement_unit,
            deleted=query.deleted,
        )
        return [material_dict_to_entity(record) for record in records]
