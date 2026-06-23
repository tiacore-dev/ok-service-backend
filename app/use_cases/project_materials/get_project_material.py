from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.project_materials import ProjectMaterial
from app.domain.project_materials import ProjectMaterialNotFoundError

from .ports import ProjectMaterialRepository


@dataclass(slots=True)
class GetProjectMaterialUseCase:
    repository: ProjectMaterialRepository

    def execute(self, project_material_id: UUID) -> ProjectMaterial:
        project_material = self.repository.get_project_material(project_material_id)
        if project_material is None:
            raise ProjectMaterialNotFoundError("Project material not found")
        return project_material
