from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.project_materials import ProjectMaterialNotFoundError

from .ports import ProjectMaterialRepository


@dataclass(slots=True)
class DeleteProjectMaterialUseCase:
    repository: ProjectMaterialRepository

    def execute(self, project_material_id: UUID) -> bool:
        deleted = self.repository.delete_project_material(project_material_id)
        if not deleted:
            raise ProjectMaterialNotFoundError("Project material not found")
        return deleted
