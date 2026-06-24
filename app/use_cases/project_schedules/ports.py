from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.project_schedules import ProjectSchedule

from .dto import ProjectScheduleListQuery


class ProjectScheduleRepository(Protocol):
    def create_project_schedule(self, schedule: ProjectSchedule) -> ProjectSchedule: ...

    def get_project_schedule(self, project_schedule_id: UUID) -> ProjectSchedule | None: ...

    def update_project_schedule(self, schedule: ProjectSchedule) -> ProjectSchedule | None: ...

    def delete_project_schedule(self, project_schedule_id: UUID) -> bool: ...

    def list_project_schedules(
        self, query: ProjectScheduleListQuery
    ) -> list[ProjectSchedule]: ...

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]: ...

    def get_schedule_ids_by_leader(self, user_id: UUID) -> list[UUID]: ...
