from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result, require_uuid
from app.database.managers.projects_managers import (
    ProjectSchedulesManager,
    ProjectsManager,
)
from app.domain.project_schedules import ProjectSchedule
from app.use_cases.project_schedules.dto import ProjectScheduleListQuery
from app.use_cases.project_schedules.ports import ProjectScheduleRepository

from .mappers import (
    project_schedule_dict_to_entity,
    project_schedule_entity_to_create_payload,
)


@dataclass(slots=True)
class SQLAlchemyProjectScheduleRepository(ProjectScheduleRepository):
    manager: ProjectSchedulesManager = field(default_factory=ProjectSchedulesManager)
    projects_manager: ProjectsManager = field(default_factory=ProjectsManager)

    def create_project_schedule(self, schedule: ProjectSchedule) -> ProjectSchedule:
        created = self.manager.add(**project_schedule_entity_to_create_payload(schedule))
        record = normalize_result(created)
        if record is None:
            raise ValueError("Project schedule creation did not return a record")
        return project_schedule_dict_to_entity(record)

    def get_project_schedule(self, project_schedule_id: UUID) -> ProjectSchedule | None:
        record = normalize_result(self.manager.get_by_id(project_schedule_id))
        if record is None:
            return None
        return project_schedule_dict_to_entity(record)

    def update_project_schedule(self, schedule: ProjectSchedule) -> ProjectSchedule | None:
        updated = self.manager.update(
            record_id=schedule.project_schedule_id,
            project=schedule.project,
            work=schedule.work,
            quantity=schedule.quantity,
            date=schedule.date,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return project_schedule_dict_to_entity(record)

    def delete_project_schedule(self, project_schedule_id: UUID) -> bool:
        deleted = self.manager.delete(record_id=project_schedule_id)
        return deleted is not None

    def list_project_schedules(
        self, query: ProjectScheduleListQuery
    ) -> list[ProjectSchedule]:
        if query.sort_by is None:
            records = self.manager.get_all_filtered(
                offset=query.offset,
                limit=query.limit,
                sort_order=query.sort_order,
                work=query.work,
                project=query.project,
                date=query.date,
            )
        else:
            records = self.manager.get_all_filtered(
                offset=query.offset,
                limit=query.limit,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
                work=query.work,
                project=query.project,
                date=query.date,
            )
        return [project_schedule_dict_to_entity(record) for record in records]

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]:
        records = self.projects_manager.get_all_filtered(project_leader=user_id)
        return [require_uuid(record["project_id"], "project_id") for record in records]

    def get_schedule_ids_by_leader(self, user_id: UUID) -> list[UUID]:
        schedule_ids = self.manager.get_schedule_ids_by_project_leader(user_id)
        return [require_uuid(schedule_id, "project_schedule_id") for schedule_id in schedule_ids]
