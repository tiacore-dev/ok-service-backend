from __future__ import annotations

from dataclasses import dataclass

from app.domain.project_schedules import ProjectSchedule

from .dto import ProjectScheduleListQuery
from .ports import ProjectScheduleRepository


@dataclass(slots=True)
class ListProjectSchedulesUseCase:
    repository: ProjectScheduleRepository

    def execute(self, query: ProjectScheduleListQuery) -> list[ProjectSchedule]:
        return self.repository.list_project_schedules(query)
