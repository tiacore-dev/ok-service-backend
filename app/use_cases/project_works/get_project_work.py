from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.project_works import ProjectWork, ProjectWorkNotFoundError

from .ports import ProjectWorkRepository


@dataclass(slots=True)
class GetProjectWorkUseCase:
    repository: ProjectWorkRepository

    def execute(self, project_work_id: UUID) -> ProjectWork:
        project_work = self.repository.get_project_work(project_work_id)
        if project_work is None:
            raise ProjectWorkNotFoundError("Project work not found")
        return project_work
