from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.projects_managers import ProjectWorksManager, ProjectsManager
from app.domain.project_works import ProjectWork
from app.use_cases.project_works.dto import ProjectWorkListQuery
from app.use_cases.project_works.ports import ProjectWorkRepository

from .mappers import (
    project_work_dict_to_entity,
    project_work_entity_to_create_payload,
)


@dataclass(slots=True)
class SQLAlchemyProjectWorkRepository(ProjectWorkRepository):
    manager: ProjectWorksManager = field(default_factory=ProjectWorksManager)
    projects_manager: ProjectsManager = field(default_factory=ProjectsManager)

    def create_project_work(self, project_work: ProjectWork) -> ProjectWork:
        created = self.manager.add(**project_work_entity_to_create_payload(project_work))
        record = normalize_result(created)
        if record is None:
            raise ValueError("Project work creation did not return a record")
        return project_work_dict_to_entity(record)

    def create_project_works(self, project_works: list[ProjectWork]) -> list[ProjectWork]:
        created_items: list[ProjectWork] = []
        for item in project_works:
            created_items.append(self.create_project_work(item))
        return created_items

    def get_project_work(self, project_work_id: UUID) -> ProjectWork | None:
        record = normalize_result(self.manager.get_by_id(project_work_id))
        if record is None:
            return None
        return project_work_dict_to_entity(record)

    def update_project_work(self, project_work: ProjectWork) -> ProjectWork | None:
        updated = self.manager.update(
            record_id=project_work.project_work_id,
            project_work_name=project_work.project_work_name,
            project=project_work.project,
            work=project_work.work,
            quantity=project_work.quantity,
            summ=project_work.summ,
            signed=project_work.signed,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return project_work_dict_to_entity(record)

    def delete_project_work(self, project_work_id: UUID) -> bool:
        deleted = self.manager.delete(project_work_id)
        return deleted is not None

    def list_project_works(self, query: ProjectWorkListQuery) -> list[ProjectWork]:
        records = self.manager.get_all_filtered(
            offset=query.offset,
            limit=query.limit,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            signed=query.signed,
            work=query.work,
            project=query.project,
            project_work_name=query.project_work_name,
            min_quantity=query.min_quantity,
            max_quantity=query.max_quantity,
            min_summ=query.min_summ,
            max_summ=query.max_summ,
        )
        return [project_work_dict_to_entity(record) for record in records]

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]:
        projects = self.projects_manager.get_projects_by_leader(user_id)
        return [UUID(project["project_id"]) for project in projects]

    def get_project_stats(self, project_id: UUID) -> dict:
        return self.projects_manager.get_project_stats(project_id)
