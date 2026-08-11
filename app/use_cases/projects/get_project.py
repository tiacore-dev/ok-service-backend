from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.projects import ProjectNotFoundError

from .ports import ProjectRepository


@dataclass(slots=True)
class GetProjectUseCase:
    repository: ProjectRepository

    def execute(self, project_id: UUID) -> dict[str, object]:
        record = self.repository.get_project_record(project_id)
        if record is None:
            raise ProjectNotFoundError("Project not found")
        return record


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
