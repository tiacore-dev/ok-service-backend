from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.database.time_utils import utc_epoch_seconds
from app.domain.work_material_relations import WorkMaterialRelation

from .dto import CreateWorkMaterialRelationCommand
from .ports import WorkMaterialRelationRepository


@dataclass(slots=True)
class CreateWorkMaterialRelationUseCase:
    repository: WorkMaterialRelationRepository

    def execute(self, command: CreateWorkMaterialRelationCommand) -> WorkMaterialRelation:
        relation = WorkMaterialRelation(
            work_material_relation_id=uuid4(),
            work=command.work,
            material=command.material,
            quantity=command.quantity,
            created_by=command.created_by,
            created_at=utc_epoch_seconds(),
        )
        return self.repository.create_work_material_relation(relation)
