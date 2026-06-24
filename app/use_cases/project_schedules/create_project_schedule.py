from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.project_schedules import (
    ProjectSchedule,
    ProjectScheduleForbiddenError,
)
from app.use_cases.time_utils import utc_epoch_seconds

from .dto import CreateProjectScheduleCommand, ProjectScheduleActor
from .ports import ProjectScheduleRepository


def _owned_project_ids(
    repository: ProjectScheduleRepository, actor: ProjectScheduleActor
) -> set[UUID]:
    return set(repository.get_project_ids_by_leader(actor.user_id))


def _owned_schedule_ids(
    repository: ProjectScheduleRepository, actor: ProjectScheduleActor
) -> set[UUID]:
    return set(repository.get_schedule_ids_by_leader(actor.user_id))


def _ensure_leader_can_use_project(
    repository: ProjectScheduleRepository,
    actor: ProjectScheduleActor,
    project_id,
    message: str,
) -> None:
    if actor.role != "project-leader":
        return
    if project_id not in _owned_project_ids(repository, actor):
        raise ProjectScheduleForbiddenError(message)


@dataclass(slots=True)
class CreateProjectScheduleUseCase:
    repository: ProjectScheduleRepository

    def execute(
        self, command: CreateProjectScheduleCommand, actor: ProjectScheduleActor
    ) -> ProjectSchedule:
        _ensure_leader_can_use_project(
            self.repository, actor, command.project, "You cannot add not your projects"
        )
        schedule = ProjectSchedule(
            project_schedule_id=uuid4(),
            project=command.project,
            work=command.work,
            quantity=command.quantity,
            date=command.date,
            created_by=command.created_by or actor.user_id,
            created_at=utc_epoch_seconds(),
        )
        return self.repository.create_project_schedule(schedule)
