from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.materials_manager import ProjectMaterialsManager
from app.database.managers.projects_managers import ProjectsManager
from app.domain.project_materials import ProjectMaterial
from app.use_cases.project_materials.dto import ProjectMaterialListQuery
from app.use_cases.project_materials.ports import ProjectMaterialRepository

from .mappers import (
    project_material_dict_to_entity,
    project_material_entity_to_create_payload,
)


@dataclass(slots=True)
class SQLAlchemyProjectMaterialRepository(ProjectMaterialRepository):
    manager: ProjectMaterialsManager = field(default_factory=ProjectMaterialsManager)
    projects_manager: ProjectsManager = field(default_factory=ProjectsManager)

    def create_project_material(
        self, project_material: ProjectMaterial
    ) -> ProjectMaterial:
        created = self.manager.add(
            **project_material_entity_to_create_payload(project_material)
        )
        record = normalize_result(created)
        if record is None:
            raise ValueError("Project material creation did not return a record")
        return project_material_dict_to_entity(record)

    def get_project_material(self, project_material_id: UUID) -> ProjectMaterial | None:
        record = normalize_result(self.manager.get_by_id(project_material_id))
        if record is None:
            return None
        return project_material_dict_to_entity(record)

    def update_project_material(
        self, project_material: ProjectMaterial
    ) -> ProjectMaterial | None:
        updated = self.manager.update(
            record_id=project_material.project_material_id,
            project=project_material.project,
            material=project_material.material,
            quantity=project_material.quantity,
            project_work=project_material.project_work,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return project_material_dict_to_entity(record)

    def delete_project_material(self, project_material_id: UUID) -> bool:
        deleted = self.manager.delete(project_material_id)
        return deleted is not None

    def list_project_materials(
        self, query: ProjectMaterialListQuery
    ) -> list[ProjectMaterial]:
        records = self.manager.get_all_filtered(
            offset=query.offset,
            limit=query.limit,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            project=query.project,
            material=query.material,
            project_work=query.project_work,
        )
        return [project_material_dict_to_entity(record) for record in records]

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]:
        projects = self.projects_manager.get_projects_by_leader(user_id)
        return [UUID(str(project["project_id"])) for project in projects]
