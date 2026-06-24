from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.materials_manager import WorkMaterialRelationsManager
from app.domain.work_material_relations import WorkMaterialRelation
from app.use_cases.work_material_relations.dto import WorkMaterialRelationListQuery
from app.use_cases.work_material_relations.ports import WorkMaterialRelationRepository

from .mappers import work_material_relation_dict_to_entity


@dataclass(slots=True)
class SQLAlchemyWorkMaterialRelationRepository(WorkMaterialRelationRepository):
    manager: WorkMaterialRelationsManager = field(default_factory=WorkMaterialRelationsManager)

    def create_work_material_relation(
        self, work_material_relation: WorkMaterialRelation
    ) -> WorkMaterialRelation:
        created = self.manager.add(
            work=work_material_relation.work,
            material=work_material_relation.material,
            quantity=work_material_relation.quantity,
            created_by=work_material_relation.created_by,
        )
        record = normalize_result(created)
        if record is None:
            raise ValueError("Work material relation creation did not return a record")
        return work_material_relation_dict_to_entity(record)

    def get_work_material_relation(
        self, work_material_relation_id: UUID
    ) -> WorkMaterialRelation | None:
        record = normalize_result(self.manager.get_by_id(work_material_relation_id))
        if record is None:
            return None
        return work_material_relation_dict_to_entity(record)

    def update_work_material_relation(
        self, work_material_relation: WorkMaterialRelation
    ) -> WorkMaterialRelation | None:
        updated = self.manager.update(
            record_id=work_material_relation.work_material_relation_id,
            work=work_material_relation.work,
            material=work_material_relation.material,
            quantity=work_material_relation.quantity,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return work_material_relation_dict_to_entity(record)

    def delete_work_material_relation(self, work_material_relation_id: UUID) -> bool:
        deleted = self.manager.delete(work_material_relation_id)
        return deleted is not None

    def list_work_material_relations(
        self, query: WorkMaterialRelationListQuery
    ) -> list[WorkMaterialRelation]:
        records = self.manager.get_all_filtered(
            offset=query.offset,
            limit=query.limit,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            work=query.work,
            material=query.material,
            created_by=query.created_by,
            created_at=query.created_at,
        )
        return [work_material_relation_dict_to_entity(record) for record in records]
