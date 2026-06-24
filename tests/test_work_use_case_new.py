from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from app.domain.works import Work, WorkNotFoundError
from app.use_cases.works import (
    CreateWorkCommand,
    CreateWorkUseCase,
    HardDeleteWorkUseCase,
    ListWorksUseCase,
    SoftDeleteWorkUseCase,
    UpdateWorkCommand,
    UpdateWorkUseCase,
    WorkListQuery,
)


@dataclass
class FakeWorkRepository:
    work: Work | None = None
    created: Work | None = None
    updated: Work | None = None
    deleted: bool = False
    listed_query: WorkListQuery | None = None

    def create_work(self, work: Work) -> Work:
        self.created = work
        self.work = work
        return work

    def get_work(self, work_id: UUID) -> Work | None:
        return self.work if self.work and self.work.work_id == work_id else None

    def update_work(self, work: Work) -> Work | None:
        self.updated = work
        self.work = work
        return work

    def delete_work(self, work_id: UUID) -> bool:
        if self.work and self.work.work_id == work_id:
            self.deleted = True
            return True
        return False

    def list_works(self, query: WorkListQuery) -> list[Work]:
        self.listed_query = query
        return [self.work] if self.work else []


def _work() -> Work:
    return Work(
        work_id=uuid4(),
        name="Test Work",
        category=None,
        measurement_unit="pcs",
        created_at=1,
        created_by=uuid4(),
        deleted=False,
    )


def test_create_work_persists_new_entity():
    repository = FakeWorkRepository()
    command = CreateWorkCommand(
        name="New Work",
        category=None,
        measurement_unit="pcs",
        created_by=uuid4(),
    )

    created = CreateWorkUseCase(repository=repository).execute(command)

    assert repository.created is created
    assert created.name == "New Work"
    assert created.deleted is False


def test_update_work_marks_deleted():
    work = _work()
    repository = FakeWorkRepository(work=work)

    updated = UpdateWorkUseCase(repository=repository).execute(
        UpdateWorkCommand(work_id=work.work_id, deleted=True)
    )

    assert updated.deleted is True
    assert repository.updated is not None


def test_soft_delete_work_sets_deleted_flag():
    work = _work()
    repository = FakeWorkRepository(work=work)

    result = SoftDeleteWorkUseCase(repository=repository).execute(work.work_id)

    assert result is True
    assert repository.updated is not None
    assert repository.updated.deleted is True


def test_hard_delete_work_requires_existing_record():
    repository = FakeWorkRepository()

    with pytest.raises(WorkNotFoundError):
        HardDeleteWorkUseCase(repository=repository).execute(uuid4())


def test_list_works_delegates_to_repository():
    work = _work()
    repository = FakeWorkRepository(work=work)

    items = ListWorksUseCase(repository=repository).execute(WorkListQuery(name="Test"))

    assert items == [work]
    assert repository.listed_query is not None
    assert repository.listed_query.name == "Test"
