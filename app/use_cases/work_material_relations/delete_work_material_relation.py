from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .ports import WorkMaterialRelationRepository


@dataclass(slots=True)
class DeleteWorkMaterialRelationUseCase:
    repository: WorkMaterialRelationRepository

    def execute(self, work_material_relation_id: UUID) -> bool:
        return self.repository.delete_work_material_relation(work_material_relation_id)
