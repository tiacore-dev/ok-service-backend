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
        if actor.role == "project-leader" and current.project_leader != actor.user_id:
            raise ProjectForbiddenError("User cannot hard delete not his shift report")
        updated = current.with_updates(deleted=True)
        return self.repository.update_project(updated) is not None


@dataclass(slots=True)
class HardDeleteProjectUseCase:
    repository: ProjectRepository

    def execute(self, project_id: UUID, actor: ProjectActor) -> bool:
        current = self.repository.get_project(project_id)
        if current is None:
            raise ProjectNotFoundError("Project not found")
        if actor.role == "project-leader" and current.project_leader != actor.user_id:
            raise ProjectForbiddenError("User cannot hard delete not his shift report")
        return self.repository.delete_project(project_id)
