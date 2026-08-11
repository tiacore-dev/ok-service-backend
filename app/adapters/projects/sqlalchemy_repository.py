from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.adapters.statistics import ProjectWorkStatistics
from app.database.managers.projects_managers import ProjectsManager
from app.domain.projects import Project, ProjectValidationError
from app.use_cases.projects.dto import ProjectActor, ProjectListQuery, ProjectStatsMap
from app.use_cases.projects.ports import ProjectRepository

from .mappers import project_dict_to_entity, project_entity_to_create_payload


@dataclass(slots=True)
class SQLAlchemyProjectRepository(ProjectRepository):
    manager: ProjectsManager = field(default_factory=ProjectsManager)
    statistics: ProjectWorkStatistics | None = None

    def create_project(self, project: Project) -> Project:
        created = self.manager.add(**project_entity_to_create_payload(project))
        record = normalize_result(created)
        if record is None:
            raise ValueError("Project creation did not return a record")
        return project_dict_to_entity(record)

    def get_project(self, project_id: UUID) -> Project | None:
        record = normalize_result(self.manager.get_by_id(project_id))
        if record is None:
            return None
        return project_dict_to_entity(record)

    def update_project(self, project: Project) -> Project | None:
        updated = self.manager.update(
            record_id=project.project_id,
            name=project.name,
            object=project.object,
            project_leader=project.project_leader,
            night_shift_available=project.night_shift_available,
            extreme_conditions_available=project.extreme_conditions_available,
            deleted=project.deleted,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return project_dict_to_entity(record)

    def delete_project(self, project_id: UUID) -> bool:
        deleted = self.manager.delete(project_id)
        if deleted is not None and self.statistics is not None:
            self.statistics.delete_project_stats(project_id)
        return deleted is not None

    def list_projects(
        self, query: ProjectListQuery, actor: ProjectActor
    ) -> list[Project]:
        records = self.manager.get_all_filtered_with_status(
            user={"role": actor.role, "user_id": str(actor.user_id)},
            offset=query.offset,
            limit=query.limit,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            name=query.name,
            deleted=query.deleted,
            object=query.object,
            project_leader=query.project_leader,
            created_by=query.created_by,
            created_at=query.created_at,
        )
        projects: list[Project] = []
        for record in records:
            try:
                projects.append(project_dict_to_entity(record))
            except ProjectValidationError as error:
                logging.warning(
                    "Skipping invalid project %s while listing projects: %s",
                    record.get("project_id"),
                    error,
                )
        return projects

    def get_project_stats(self, project_id: UUID) -> ProjectStatsMap:
        if self.statistics is None:
            return {}
        return self.statistics.get_project_stats(project_id)

    def get_project_stats_by_materials(self, project_id: UUID) -> ProjectStatsMap:
        return self.manager.get_project_stats_by_project_materials(project_id)
