from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.project_schedules import (
    ProjectSchedule,
    ProjectScheduleNotFoundError,
)

from .ports import ProjectScheduleRepository


@dataclass(slots=True)
class GetProjectScheduleUseCase:
    repository: ProjectScheduleRepository

    def execute(self, project_schedule_id: UUID) -> ProjectSchedule:
        schedule = self.repository.get_project_schedule(project_schedule_id)
        if schedule is None:
            raise ProjectScheduleNotFoundError("Project schedule not found")
        return schedule
