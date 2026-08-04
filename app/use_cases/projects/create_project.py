from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.use_cases.time_utils import utc_epoch_milliseconds
from app.domain.projects import Project

from .dto import CreateProjectCommand, ProjectActor
from .ports import ProjectRepository


@dataclass(slots=True)
class CreateProjectUseCase:
    repository: ProjectRepository

    def execute(self, command: CreateProjectCommand, actor: ProjectActor) -> Project:
        project_leader = command.project_leader
        if actor.role == "project-leader":
            project_leader = actor.user_id
        project = Project(
            project_id=uuid4(),
            name=command.name,
            object=command.object,
            project_leader=project_leader,
            night_shift_available=command.night_shift_available,
            extreme_conditions_available=command.extreme_conditions_available,
            created_by=command.created_by or actor.user_id,
            created_at=utc_epoch_milliseconds(),
            deleted=False,
        )
        return self.repository.create_project(project)
