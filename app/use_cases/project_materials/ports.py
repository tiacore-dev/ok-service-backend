from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.project_materials import ProjectMaterial

from .dto import ProjectMaterialListQuery


class ProjectMaterialRepository(Protocol):
    def create_project_material(self, project_material: ProjectMaterial) -> ProjectMaterial: ...

    def get_project_material(self, project_material_id: UUID) -> ProjectMaterial | None: ...

    def update_project_material(self, project_material: ProjectMaterial) -> ProjectMaterial | None: ...

    def delete_project_material(self, project_material_id: UUID) -> bool: ...

    def list_project_materials(self, query: ProjectMaterialListQuery) -> list[ProjectMaterial]: ...
