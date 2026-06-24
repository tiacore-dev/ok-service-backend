from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.project_schedules import (
    ProjectScheduleForbiddenError,
    ProjectScheduleNotFoundError,
)

from .create_project_schedule import _owned_schedule_ids
from .dto import ProjectScheduleActor
from .ports import ProjectScheduleRepository


@dataclass(slots=True)
class HardDeleteProjectScheduleUseCase:
    repository: ProjectScheduleRepository

    def execute(self, project_schedule_id: UUID, actor: ProjectScheduleActor) -> bool:
        current = self.repository.get_project_schedule(project_schedule_id)
        if current is None:
            raise ProjectScheduleNotFoundError("Project schedule not found")

        if actor.role == "project-leader":
            if current.project_schedule_id not in _owned_schedule_ids(self.repository, actor):
                raise ProjectScheduleForbiddenError("Forbidden")

        deleted = self.repository.delete_project_schedule(project_schedule_id)
        if not deleted:
            raise ProjectScheduleNotFoundError("Project schedule not found")
        return deleted
