from __future__ import annotations

from dataclasses import dataclass

from .dto import WorkMaterialRelationListQuery
from .ports import WorkMaterialRelationRepository


@dataclass(slots=True)
class ListWorkMaterialRelationsUseCase:
    repository: WorkMaterialRelationRepository

    def execute(self, query: WorkMaterialRelationListQuery):
        return self.repository.list_work_material_relations(query)
