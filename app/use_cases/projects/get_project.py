from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.projects import Project, ProjectNotFoundError

from .ports import ProjectRepository


@dataclass(slots=True)
class GetProjectUseCase:
    repository: ProjectRepository

    def execute(self, project_id: UUID) -> Project:
        project = self.repository.get_project(project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        return project


@dataclass(slots=True)
class GetProjectStatsUseCase:
    repository: ProjectRepository

    def execute(self, project_id: UUID):
        return self.repository.get_project_stats(project_id)


@dataclass(slots=True)
class GetProjectStatsByMaterialsUseCase:
    repository: ProjectRepository

    def execute(self, project_id: UUID):
        return self.repository.get_project_stats_by_materials(project_id)
