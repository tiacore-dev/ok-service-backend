from __future__ import annotations

from dataclasses import dataclass

from app.domain.project_materials import ProjectMaterial

from .dto import ProjectMaterialListQuery
from .ports import ProjectMaterialRepository


@dataclass(slots=True)
class ListProjectMaterialsUseCase:
    repository: ProjectMaterialRepository

    def execute(self, query: ProjectMaterialListQuery) -> list[ProjectMaterial]:
        return self.repository.list_project_materials(query)
