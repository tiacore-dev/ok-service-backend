from __future__ import annotations

from dataclasses import dataclass

from app.domain.project_materials import ProjectMaterial, ProjectMaterialNotFoundError

from .dto import UpdateProjectMaterialCommand
from .ports import ProjectMaterialRepository


@dataclass(slots=True)
class UpdateProjectMaterialUseCase:
    repository: ProjectMaterialRepository

    def execute(self, command: UpdateProjectMaterialCommand) -> ProjectMaterial:
        current = self.repository.get_project_material(command.project_material_id)
        if current is None:
            raise ProjectMaterialNotFoundError("Project material not found")

        changes: dict[str, object] = {}
        if command.project_is_set:
            changes["project"] = command.project
        if command.material_is_set:
            changes["material"] = command.material
        if command.quantity_is_set:
            changes["quantity"] = command.quantity
        if command.project_work_is_set:
            changes["project_work"] = command.project_work

        if not changes:
            return current

        updated = current.with_updates(**changes)
        result = self.repository.update_project_material(updated)
        if result is None:
            raise ProjectMaterialNotFoundError("Project material not found")
        return result
