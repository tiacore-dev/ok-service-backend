from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from app.domain.project_schedules import (
    ProjectSchedule,
    ProjectScheduleForbiddenError,
    ProjectScheduleNotFoundError,
)
from app.use_cases.project_schedules import (
    CreateProjectScheduleCommand,
    CreateProjectScheduleUseCase,
    GetProjectScheduleUseCase,
    HardDeleteProjectScheduleUseCase,
    ListProjectSchedulesUseCase,
    ProjectScheduleActor,
    ProjectScheduleListQuery,
    UpdateProjectScheduleCommand,
    UpdateProjectScheduleUseCase,
)


@dataclass
class FakeProjectScheduleRepository:
    schedule: ProjectSchedule | None = None
    created: ProjectSchedule | None = None
    updated: ProjectSchedule | None = None
    deleted: UUID | None = None
    listed_query: ProjectScheduleListQuery | None = None
    project_ids_by_leader: list[UUID] | None = None
    schedule_ids_by_leader: list[UUID] | None = None

    def create_project_schedule(self, schedule: ProjectSchedule) -> ProjectSchedule:
        self.created = schedule
        self.schedule = schedule
        return schedule

    def get_project_schedule(self, project_schedule_id: UUID) -> ProjectSchedule | None:
        return (
            self.schedule
            if self.schedule and self.schedule.project_schedule_id == project_schedule_id
            else None
        )

    def update_project_schedule(self, schedule: ProjectSchedule) -> ProjectSchedule | None:
        self.updated = schedule
        self.schedule = schedule
        return schedule

    def delete_project_schedule(self, project_schedule_id: UUID) -> bool:
        self.deleted = project_schedule_id
        return self.schedule is not None and self.schedule.project_schedule_id == project_schedule_id

    def list_project_schedules(
        self, query: ProjectScheduleListQuery
    ) -> list[ProjectSchedule]:
        self.listed_query = query
        return [self.schedule] if self.schedule is not None else []

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]:
        return self.project_ids_by_leader or []

    def get_schedule_ids_by_leader(self, user_id: UUID) -> list[UUID]:
        return self.schedule_ids_by_leader or []


def _schedule() -> ProjectSchedule:
    return ProjectSchedule(
        project_schedule_id=uuid4(),
        project=uuid4(),
        work=uuid4(),
        quantity=12.5,
        created_by=uuid4(),
        created_at=1,
        date=20240101,
    )


def test_create_project_schedule_use_case_checks_project_ownership():
    project_id = uuid4()
    repository = FakeProjectScheduleRepository(project_ids_by_leader=[project_id])
    actor = ProjectScheduleActor(role="project-leader", user_id=uuid4())

    result = CreateProjectScheduleUseCase(repository=repository).execute(
        CreateProjectScheduleCommand(
            project=project_id,
            work=uuid4(),
            quantity=1.0,
        ),
        actor,
    )

    assert result == repository.created
    assert result.created_by == actor.user_id


def test_create_project_schedule_use_case_rejects_foreign_project():
    repository = FakeProjectScheduleRepository(project_ids_by_leader=[uuid4()])
    actor = ProjectScheduleActor(role="project-leader", user_id=uuid4())

    with pytest.raises(ProjectScheduleForbiddenError, match="You cannot add not your projects"):
        CreateProjectScheduleUseCase(repository=repository).execute(
            CreateProjectScheduleCommand(project=uuid4(), work=uuid4(), quantity=1.0),
            actor,
        )


def test_update_project_schedule_use_case_rejects_foreign_schedule():
    schedule = _schedule()
    repository = FakeProjectScheduleRepository(
        schedule=schedule,
        schedule_ids_by_leader=[uuid4()],
    )
    actor = ProjectScheduleActor(role="project-leader", user_id=uuid4())

    with pytest.raises(ProjectScheduleForbiddenError, match="Forbidden"):
        UpdateProjectScheduleUseCase(repository=repository).execute(
            UpdateProjectScheduleCommand(
                project_schedule_id=schedule.project_schedule_id,
                quantity=20.0,
            ),
            actor,
        )


def test_update_project_schedule_use_case_updates_quantity():
    schedule = _schedule()
    repository = FakeProjectScheduleRepository(
        schedule=schedule,
        schedule_ids_by_leader=[schedule.project_schedule_id],
    )
    actor = ProjectScheduleActor(role="project-leader", user_id=uuid4())

    result = UpdateProjectScheduleUseCase(repository=repository).execute(
        UpdateProjectScheduleCommand(
            project_schedule_id=schedule.project_schedule_id,
            quantity=20.0,
        ),
        actor,
    )

    assert result.quantity == 20.0
    assert repository.updated is not None


def test_delete_project_schedule_use_case_rejects_missing_schedule():
    repository = FakeProjectScheduleRepository()
    actor = ProjectScheduleActor(role="admin", user_id=uuid4())

    with pytest.raises(ProjectScheduleNotFoundError):
        HardDeleteProjectScheduleUseCase(repository=repository).execute(uuid4(), actor)


def test_list_project_schedules_use_case_delegates_query():
    schedule = _schedule()
    repository = FakeProjectScheduleRepository(schedule=schedule)
    query = ProjectScheduleListQuery(project=schedule.project)

    result = ListProjectSchedulesUseCase(repository=repository).execute(query)

    assert result == [schedule]
    assert repository.listed_query == query


def test_get_project_schedule_use_case_returns_record():
    schedule = _schedule()
    repository = FakeProjectScheduleRepository(schedule=schedule)

    result = GetProjectScheduleUseCase(repository=repository).execute(
        schedule.project_schedule_id
    )

    assert result == schedule
