from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.projects import (
    Project,
    ProjectConflictError,
    ProjectForbiddenError,
    ProjectNotFoundError,
    ProjectStatus,
)

from .dto import ProjectActor
from .ports import ProjectRepository


@dataclass(slots=True)
class UpdateProjectStatusUseCase:
    repository: ProjectRepository

    def execute(
        self, project_id: UUID, status: ProjectStatus, actor: ProjectActor
    ) -> Project:
        if actor.role not in {"admin", "manager"}:
            raise ProjectForbiddenError(
                "Only admin or manager can change project status"
            )
        current = self.repository.get_project(project_id)
        if current is None or current.deleted:
            raise ProjectNotFoundError("Project not found")
        if status != current.status and status not in ProjectStatus.neighbours(
            current.status
        ):
            raise ValueError("Project status can only move to the adjacent status")
        updated = self.repository.update_project_status(
            project_id, current.status, status
        )
        if updated is None:
            raise ProjectConflictError("Project status was changed by another request")
        return updated
