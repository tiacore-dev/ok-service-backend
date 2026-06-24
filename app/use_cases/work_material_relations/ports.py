from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.work_material_relations import WorkMaterialRelation

from .dto import WorkMaterialRelationListQuery


class WorkMaterialRelationRepository(Protocol):
    def create_work_material_relation(
        self, work_material_relation: WorkMaterialRelation
    ) -> WorkMaterialRelation: ...

    def get_work_material_relation(
        self, work_material_relation_id: UUID
    ) -> WorkMaterialRelation | None: ...

    def update_work_material_relation(
        self, work_material_relation: WorkMaterialRelation
    ) -> WorkMaterialRelation | None: ...

    def delete_work_material_relation(self, work_material_relation_id: UUID) -> bool: ...

    def list_work_material_relations(
        self, query: WorkMaterialRelationListQuery
    ) -> list[WorkMaterialRelation]: ...
