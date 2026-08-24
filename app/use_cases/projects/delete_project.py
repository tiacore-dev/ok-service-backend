from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.projects import ProjectForbiddenError, ProjectNotFoundError

from .dto import ProjectActor
from .ports import ProjectRepository


@dataclass(slots=True)
class SoftDeleteProjectUseCase:
    repository: ProjectRepository

    def execute(self, project_id: UUID, actor: ProjectActor) -> bool:
        current = self.repository.get_project(project_id)
        if current is None:
            raise ProjectNotFoundError("Project not found")
        if actor.role != "admin":
            raise ProjectForbiddenError("Forbidden")
        updated = current.with_updates(deleted=True)
        return self.repository.update_project(updated) is not None


@dataclass(slots=True)
class HardDeleteProjectUseCase:
    repository: ProjectRepository

    def execute(self, project_id: UUID, actor: ProjectActor) -> bool:
        current = self.repository.get_project(project_id)
        if current is None:
            raise ProjectNotFoundError("Project not found")
        if actor.role != "admin":
            raise ProjectForbiddenError("Forbidden")
        return self.repository.delete_project(project_id)
