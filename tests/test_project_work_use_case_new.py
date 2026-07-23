from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.project_works import ProjectWork, ProjectWorkForbiddenError
from app.use_cases.project_works import (
    BulkCreateProjectWorksCommand,
    BulkCreateProjectWorksUseCase,
    CreateProjectWorkCommand,
    CreateProjectWorkUseCase,
    DeleteProjectWorkUseCase,
    ProjectWorkActor,
    ProjectWorkListQuery,
    SoftDeleteProjectWorkUseCase,
    UpdateProjectWorkCommand,
    UpdateProjectWorkUseCase,
)


class FakeProjectWorkRepository:
    def __init__(self, project_work: ProjectWork | None = None, owned_projects=None):
        self.project_work = project_work
        self.owned_projects = owned_projects or []
        self.created = []
        self.updated = None
        self.deleted = None
        self.last_query = None

    def create_project_work(self, project_work: ProjectWork) -> ProjectWork:
        self.created.append(project_work)
        self.project_work = project_work
        return project_work

    def create_project_works(self, project_works: list[ProjectWork]) -> list[ProjectWork]:
        self.created.extend(project_works)
        if project_works:
            self.project_work = project_works[-1]
        return project_works

    def get_project_work(self, project_work_id):
        if self.project_work and self.project_work.project_work_id == project_work_id:
            return self.project_work
        return None

    def update_project_work(self, project_work: ProjectWork):
        self.updated = project_work
        self.project_work = project_work
        return project_work

    def delete_project_work(self, project_work_id):
        self.deleted = project_work_id
        return self.project_work is not None and self.project_work.project_work_id == project_work_id

    def list_project_works(self, query: ProjectWorkListQuery):
        self.last_query = query
        return [self.project_work] if self.project_work is not None else []

    def get_project_ids_by_leader(self, user_id):
        return self.owned_projects

    def get_project_stats(self, project_id):
        return {}


def _actor(role="admin"):
    return ProjectWorkActor(role=role, user_id=uuid4())


def test_create_project_work_for_leader_forces_signed_false():
    project_id = uuid4()
    repository = FakeProjectWorkRepository(owned_projects=[project_id])
    command = CreateProjectWorkCommand(
        project=project_id,
        project_work_name="Test work",
        work=uuid4(),
        quantity=Decimal("2.5"),
        summ=Decimal("10.0"),
        signed=True,
        created_by=uuid4(),
    )

    result = CreateProjectWorkUseCase(repository=repository).execute(
        command, _actor("project-leader")
    )

    assert result.signed is False
    assert repository.created[0].signed is False


def test_create_project_work_for_leader_rejects_foreign_project():
    repository = FakeProjectWorkRepository(owned_projects=[uuid4()])
    command = CreateProjectWorkCommand(
        project=uuid4(),
        project_work_name="Test work",
        work=uuid4(),
        quantity=Decimal("2.5"),
        created_by=uuid4(),
    )

    with pytest.raises(ProjectWorkForbiddenError, match="You cannot add not your projects"):
        CreateProjectWorkUseCase(repository=repository).execute(
            command, _actor("project-leader")
        )


def test_bulk_create_project_works_for_leader():
    project_id = uuid4()
    repository = FakeProjectWorkRepository(owned_projects=[project_id])
    command = BulkCreateProjectWorksCommand(
        project_works=[
            CreateProjectWorkCommand(
                project=project_id,
                project_work_name="One",
                work=uuid4(),
                quantity=Decimal("1.0"),
                created_by=uuid4(),
            ),
            CreateProjectWorkCommand(
                project=project_id,
                project_work_name="Two",
                work=uuid4(),
                quantity=Decimal("2.0"),
                created_by=uuid4(),
            ),
        ]
    )

    result = BulkCreateProjectWorksUseCase(repository=repository).execute(
        command, _actor("project-leader")
    )

    assert len(result) == 2
    assert all(item.signed is False for item in result)


def test_update_project_work_use_case():
    project_work = ProjectWork(
        project_work_id=uuid4(),
        project_work_name="Test work",
        project=uuid4(),
        work=uuid4(),
        quantity=Decimal("3.0"),
        summ=Decimal("12.0"),
        created_by=uuid4(),
        created_at=1,
        signed=False,
    )
    repository = FakeProjectWorkRepository(project_work=project_work)

    result = UpdateProjectWorkUseCase(repository=repository).execute(
        UpdateProjectWorkCommand(
            project_work_id=project_work.project_work_id,
            quantity=Decimal("4.0"),
        ),
        _actor("admin"),
    )

    assert result.quantity == Decimal("4.0")


def test_update_project_work_forbidden_for_foreign_project_leader():
    project_work = ProjectWork(
        project_work_id=uuid4(),
        project_work_name="Test work",
        project=uuid4(),
        work=uuid4(),
        quantity=Decimal("3.0"),
        summ=Decimal("12.0"),
        created_by=uuid4(),
        created_at=1,
        signed=False,
    )
    repository = FakeProjectWorkRepository(project_work=project_work, owned_projects=[uuid4()])

    with pytest.raises(ProjectWorkForbiddenError, match="Forbidden"):
        UpdateProjectWorkUseCase(repository=repository).execute(
            UpdateProjectWorkCommand(
                project_work_id=project_work.project_work_id,
                quantity=Decimal("4.0"),
            ),
            _actor("project-leader"),
        )


def test_soft_delete_project_work_use_case():
    project_work = ProjectWork(
        project_work_id=uuid4(),
        project_work_name="Test work",
        project=uuid4(),
        work=uuid4(),
        quantity=Decimal("3.0"),
        summ=Decimal("12.0"),
        created_by=uuid4(),
        created_at=1,
        signed=True,
    )
    repository = FakeProjectWorkRepository(project_work=project_work)

    result = SoftDeleteProjectWorkUseCase(repository=repository).execute(
        project_work.project_work_id,
        _actor("admin"),
    )

    assert result.signed is False


def test_delete_project_work_use_case():
    project_work = ProjectWork(
        project_work_id=uuid4(),
        project_work_name="Test work",
        project=uuid4(),
        work=uuid4(),
        quantity=Decimal("3.0"),
        summ=Decimal("12.0"),
        created_by=uuid4(),
        created_at=1,
        signed=False,
    )
    repository = FakeProjectWorkRepository(project_work=project_work)

    result = DeleteProjectWorkUseCase(repository=repository).execute(
        project_work.project_work_id,
        _actor("admin"),
    )

    assert result is True
    assert repository.deleted == project_work.project_work_id
