from __future__ import annotations

from dataclasses import dataclass

from app.domain.projects import Project, ProjectForbiddenError, ProjectNotFoundError

from .dto import ProjectActor, UpdateProjectCommand
from .ports import ProjectRepository


@dataclass(slots=True)
class UpdateProjectUseCase:
    repository: ProjectRepository

    def execute(self, command: UpdateProjectCommand, actor: ProjectActor) -> Project:
        current = self.repository.get_project(command.project_id)
        if current is None:
            raise ProjectNotFoundError("Project not found")

        if actor.role == "project-leader" and current.project_leader != actor.user_id:
            raise ProjectForbiddenError("User cannot edit not his shift report")

        updated = current.with_updates(
            name=command.name,
            object=command.object,
            project_leader=command.project_leader,
            night_shift_available=command.night_shift_available,
            extreme_conditions_available=command.extreme_conditions_available,
            deleted=command.deleted,
        )
        result = self.repository.update_project(updated)
        if result is None:
            raise ProjectNotFoundError("Project not found")
        return result
