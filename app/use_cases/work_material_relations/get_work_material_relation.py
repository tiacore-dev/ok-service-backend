from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.work_material_relations import WorkMaterialRelationNotFoundError

from .ports import WorkMaterialRelationRepository


@dataclass(slots=True)
class GetWorkMaterialRelationUseCase:
    repository: WorkMaterialRelationRepository

    def execute(self, work_material_relation_id: UUID):
        relation = self.repository.get_work_material_relation(work_material_relation_id)
        if relation is None:
            raise WorkMaterialRelationNotFoundError("Work material relation not found")
        return relation
