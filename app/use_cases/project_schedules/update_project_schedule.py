from __future__ import annotations

from dataclasses import dataclass

from app.domain.project_schedules import (
    ProjectSchedule,
    ProjectScheduleForbiddenError,
    ProjectScheduleNotFoundError,
)

from .dto import ProjectScheduleActor, UpdateProjectScheduleCommand
from .create_project_schedule import _owned_schedule_ids
from .ports import ProjectScheduleRepository


@dataclass(slots=True)
class UpdateProjectScheduleUseCase:
    repository: ProjectScheduleRepository

    def execute(
        self, command: UpdateProjectScheduleCommand, actor: ProjectScheduleActor
    ) -> ProjectSchedule:
        current = self.repository.get_project_schedule(command.project_schedule_id)
        if current is None:
            raise ProjectScheduleNotFoundError("Project schedule not found")

        if actor.role == "project-leader":
            if current.project_schedule_id not in _owned_schedule_ids(self.repository, actor):
                raise ProjectScheduleForbiddenError("Forbidden")

        updated = current.with_updates(
            project=command.project,
            work=command.work,
            quantity=command.quantity,
            date=command.date,
        )
        result = self.repository.update_project_schedule(updated)
        if result is None:
            raise ProjectScheduleNotFoundError("Project schedule not found")
        return result
