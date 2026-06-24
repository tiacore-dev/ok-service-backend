from __future__ import annotations

from dataclasses import dataclass

from app.domain.work_material_relations import WorkMaterialRelationNotFoundError

from .dto import UpdateWorkMaterialRelationCommand
from .ports import WorkMaterialRelationRepository


@dataclass(slots=True)
class UpdateWorkMaterialRelationUseCase:
    repository: WorkMaterialRelationRepository

    def execute(self, command: UpdateWorkMaterialRelationCommand):
        existing = self.repository.get_work_material_relation(
            command.work_material_relation_id
        )
        if existing is None:
            raise WorkMaterialRelationNotFoundError("Work material relation not found")

        changes = {}
        if command.work is not None:
            changes["work"] = command.work
        if command.material is not None:
            changes["material"] = command.material
        if command.quantity is not None:
            changes["quantity"] = command.quantity
        if not changes:
            return existing

        result = self.repository.update_work_material_relation(
            existing.with_updates(**changes)
        )
        if result is None:
            raise WorkMaterialRelationNotFoundError("Work material relation not found")
        return result
