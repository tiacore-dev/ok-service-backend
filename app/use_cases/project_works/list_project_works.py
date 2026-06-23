from __future__ import annotations

from dataclasses import dataclass

from app.domain.project_works import ProjectWork

from .dto import ProjectWorkListQuery
from .ports import ProjectWorkRepository


@dataclass(slots=True)
class ListProjectWorksUseCase:
    repository: ProjectWorkRepository

    def execute(self, query: ProjectWorkListQuery) -> list[ProjectWork]:
        return self.repository.list_project_works(query)
