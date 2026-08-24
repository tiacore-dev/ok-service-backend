from __future__ import annotations

from dataclasses import dataclass

from app.domain.projects import ProjectForbiddenError

from .dto import ProjectActor, ProjectListQuery
from .ports import ProjectRepository


@dataclass(slots=True)
class ListProjectsUseCase:
    repository: ProjectRepository

    def execute(
        self, query: ProjectListQuery, actor: ProjectActor
    ) -> list[dict[str, object]]:
        return self.repository.list_project_records(query, actor)
