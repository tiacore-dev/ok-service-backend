from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.project_works import (
    ProjectWork,
    ProjectWorkForbiddenError,
    ProjectWorkNotFoundError,
)

from .create_project_work import _owned_project_ids
from .dto import ProjectWorkActor
from .ports import ProjectWorkRepository


@dataclass(slots=True)
class SoftDeleteProjectWorkUseCase:
    repository: ProjectWorkRepository

    def execute(self, project_work_id: UUID, actor: ProjectWorkActor) -> ProjectWork:
        current = self.repository.get_project_work(project_work_id)
        if current is None:
            raise ProjectWorkNotFoundError("Project work not found")

        if actor.role == "project-leader":
            owned_project_ids = _owned_project_ids(self.repository, actor)
            if current.project not in owned_project_ids:
                raise ProjectWorkForbiddenError("Forbidden")
            if current.signed is True:
                raise ProjectWorkForbiddenError(
                    "User cannot soft delete signed shift report"
                )

        updated = self.repository.update_project_work(
            current.with_updates(signed=False)
        )
        if updated is None:
            raise ProjectWorkNotFoundError("Project work not found")
        return updated


@dataclass(slots=True)
class DeleteProjectWorkUseCase:
    repository: ProjectWorkRepository

    def execute(self, project_work_id: UUID, actor: ProjectWorkActor) -> bool:
        current = self.repository.get_project_work(project_work_id)
        if current is None:
            raise ProjectWorkNotFoundError("Project work not found")

        if actor.role == "project-leader":
            owned_project_ids = _owned_project_ids(self.repository, actor)
            if current.project not in owned_project_ids:
                raise ProjectWorkForbiddenError("Forbidden")
            if current.signed is True:
                raise ProjectWorkForbiddenError(
                    "User cannot hard delete signed shift report"
                )

        deleted = self.repository.delete_project_work(project_work_id)
        if not deleted:
            raise ProjectWorkNotFoundError("Project work not found")
        return deleted


# Backward-compatible alias names for clarity in routes.
HardDeleteProjectWorkUseCase = DeleteProjectWorkUseCase
