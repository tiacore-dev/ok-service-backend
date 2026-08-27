from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.project_materials import (
    ProjectMaterialForbiddenError,
    ProjectMaterialNotFoundError,
)

from .dto import ProjectMaterialActor
from .ports import ProjectMaterialRepository


@dataclass(slots=True)
class DeleteProjectMaterialUseCase:
    repository: ProjectMaterialRepository

    def execute(self, project_material_id: UUID, actor: ProjectMaterialActor) -> bool:
        current = self.repository.get_project_material(project_material_id)
        if current is None:
            raise ProjectMaterialNotFoundError("Project material not found")
        if actor.role not in {"admin", "manager"}:
            if actor.role != "project-leader":
                raise ProjectMaterialForbiddenError("Forbidden")
            if current.project not in self.repository.get_project_ids_by_leader(
                actor.user_id
            ):
                raise ProjectMaterialForbiddenError(
                    "You cannot delete material outside your project"
                )
        deleted = self.repository.delete_project_material(project_material_id)
        if not deleted:
            raise ProjectMaterialNotFoundError("Project material not found")
        return deleted
