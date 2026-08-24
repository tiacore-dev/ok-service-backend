from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from app.domain.projects import (
    Project,
    ProjectForbiddenError,
    ProjectNotFoundError,
    ProjectValidationError,
)
from app.adapters.projects import SQLAlchemyProjectRepository, project_dict_to_entity
from app.database.managers.projects_managers import ProjectsManager
from app.use_cases.projects import (
    CreateProjectCommand,
    CreateProjectUseCase,
    GetProjectStatsByMaterialsUseCase,
    GetProjectStatsUseCase,
    GetProjectUseCase,
    HardDeleteProjectUseCase,
    ListProjectsUseCase,
    ProjectActor,
    ProjectListQuery,
    SoftDeleteProjectUseCase,
    UpdateProjectCommand,
    UpdateProjectUseCase,
)


@dataclass
class FakeProjectRepository:
    project: Project | None = None
    created: Project | None = None
    updated: Project | None = None
    deleted: UUID | None = None
    listed_query: ProjectListQuery | None = None
    listed_actor: ProjectActor | None = None
    stats: dict[str, dict[str, object]] | None = None
    stats_by_materials: dict[str, dict[str, object]] | None = None

    def create_project(self, project: Project) -> Project:
        self.created = project
        self.project = project
        return project

    def get_project(self, project_id: UUID) -> Project | None:
        return self.project if self.project and self.project.project_id == project_id else None

    def get_project_record(self, project_id: UUID) -> dict[str, object] | None:
        if self.project is None or self.project.project_id != project_id:
            return None
        return {"project_id": str(self.project.project_id), "name": self.project.name}

    def update_project(self, project: Project) -> Project | None:
        self.updated = project
        self.project = project
        return project

    def delete_project(self, project_id: UUID) -> bool:
        self.deleted = project_id
        return self.project is not None and self.project.project_id == project_id

    def list_projects(self, query: ProjectListQuery, actor: ProjectActor) -> list[Project]:
        self.listed_query = query
        self.listed_actor = actor
        return [self.project] if self.project is not None else []

    def list_project_records(
        self, query: ProjectListQuery, actor: ProjectActor
    ) -> list[dict[str, object]]:
        self.listed_query = query
        self.listed_actor = actor
        return (
            [{"project_id": str(self.project.project_id), "name": self.project.name}]
            if self.project is not None
            else []
        )

    def get_project_stats(self, project_id: UUID) -> dict[str, dict[str, object]]:
        return self.stats or {str(project_id): {"project_work_quantity": 0}}

    def get_project_stats_by_materials(self, project_id: UUID) -> dict[str, dict[str, object]]:
        return self.stats_by_materials or {
            str(project_id): {"project_work_quantity": 0}
        }


def _project() -> Project:
    return Project(
        project_id=uuid4(),
        name="New project",
        object=uuid4(),
        project_leader=uuid4(),
        night_shift_available=False,
        extreme_conditions_available=True,
        created_by=uuid4(),
        created_at=1,
        deleted=False,
    )


def test_create_project_use_case_forces_project_leader_for_project_leader_role():
    repository = FakeProjectRepository()
    actor = ProjectActor(role="project-leader", user_id=uuid4())
    command = CreateProjectCommand(
        name="Project A",
        object=uuid4(),
        project_leader=uuid4(),
        created_by=uuid4(),
    )

    result = CreateProjectUseCase(repository=repository).execute(command, actor)

    assert result == repository.created
    assert result.project_leader == actor.user_id
    assert result.created_by == command.created_by


def test_create_project_use_case_rejects_empty_name():
    repository = FakeProjectRepository()
    actor = ProjectActor(role="admin", user_id=uuid4())

    with pytest.raises(ProjectValidationError, match="Project name is required"):
        CreateProjectUseCase(repository=repository).execute(
            CreateProjectCommand(name="   ", object=uuid4(), created_by=uuid4()),
            actor,
        )


def test_update_project_use_case_rejects_foreign_project_for_project_leader():
    project = _project()
    repository = FakeProjectRepository(project=project)
    actor = ProjectActor(role="project-leader", user_id=uuid4())

    with pytest.raises(ProjectForbiddenError, match="User cannot edit not his shift report"):
        UpdateProjectUseCase(repository=repository).execute(
            UpdateProjectCommand(project_id=project.project_id, name="Edited"),
            actor,
        )


def test_update_project_use_case_updates_project_name():
    project = _project()
    repository = FakeProjectRepository(project=project)
    actor = ProjectActor(role="admin", user_id=uuid4())

    result = UpdateProjectUseCase(repository=repository).execute(
        UpdateProjectCommand(project_id=project.project_id, name="Edited"),
        actor,
    )

    assert result.name == "Edited"
    assert repository.updated is not None


def test_update_project_use_case_rejects_empty_name():
    project = _project()
    repository = FakeProjectRepository(project=project)
    actor = ProjectActor(role="admin", user_id=uuid4())

    with pytest.raises(ProjectValidationError, match="Project name is required"):
        UpdateProjectUseCase(repository=repository).execute(
            UpdateProjectCommand(project_id=project.project_id, name="   "),
            actor,
        )


def test_soft_delete_project_use_case_rejects_foreign_project_for_project_leader():
    project = _project()
    repository = FakeProjectRepository(project=project)
    actor = ProjectActor(role="project-leader", user_id=uuid4())

    with pytest.raises(ProjectForbiddenError, match="Forbidden"):
        SoftDeleteProjectUseCase(repository=repository).execute(project.project_id, actor)


def test_hard_delete_project_use_case_deletes_project():
    project = _project()
    repository = FakeProjectRepository(project=project)
    actor = ProjectActor(role="admin", user_id=uuid4())

    result = HardDeleteProjectUseCase(repository=repository).execute(project.project_id, actor)

    assert result is True
    assert repository.deleted == project.project_id


def test_get_project_use_case_raises_for_missing_project():
    repository = FakeProjectRepository()

    with pytest.raises(ProjectNotFoundError):
        GetProjectUseCase(repository=repository).execute(
            uuid4(), ProjectActor(role="admin", user_id=uuid4())
        )


def test_list_projects_use_case_delegates_query_and_actor():
    project = _project()
    repository = FakeProjectRepository(project=project)
    query = ProjectListQuery(name="New")
    actor = ProjectActor(role="manager", user_id=uuid4())

    result = ListProjectsUseCase(repository=repository).execute(query, actor)

    assert result == [{"project_id": str(project.project_id), "name": project.name}]
    assert repository.listed_query == query
    assert repository.listed_actor == actor


def test_project_reads_allow_user_but_stats_remain_restricted():
    project = _project()
    repository = FakeProjectRepository(project=project)
    actor = ProjectActor(role="user", user_id=uuid4())

    assert GetProjectUseCase(repository).execute(project.project_id, actor)
    assert ListProjectsUseCase(repository).execute(ProjectListQuery(), actor)
    with pytest.raises(ProjectForbiddenError):
        GetProjectStatsUseCase(repository).execute(project.project_id, actor)


def test_project_delete_is_admin_only():
    project = _project()
    repository = FakeProjectRepository(project=project)
    with pytest.raises(ProjectForbiddenError):
        SoftDeleteProjectUseCase(repository).execute(
            project.project_id, ProjectActor("manager", uuid4())
        )


def test_project_stats_use_cases_delegate_to_repository():
    project = _project()
    repository = FakeProjectRepository(
        project=project,
        stats={str(project.project_id): {"project_work_quantity": 3}},
        stats_by_materials={str(project.project_id): {"project_work_quantity": 5}},
    )

    actor = ProjectActor(role="admin", user_id=uuid4())
    assert GetProjectStatsUseCase(repository=repository).execute(project.project_id, actor) == repository.stats
    assert (
        GetProjectStatsByMaterialsUseCase(repository=repository).execute(project.project_id, actor)
        == repository.stats_by_materials
    )


def test_project_mapper_treats_string_none_as_missing_created_by():
    project_id = uuid4()
    payload = {
        "project_id": str(project_id),
        "name": "Mapped",
        "object": str(uuid4()),
        "project_leader": None,
        "night_shift_available": False,
        "extreme_conditions_available": True,
        "created_by": "None",
        "created_at": 1,
        "deleted": False,
    }

    project = project_dict_to_entity(payload)

    assert project.project_id == project_id
    assert project.created_by is None


def test_project_repository_list_keeps_invalid_legacy_records_for_reads():
    valid_project = _project()
    valid_record = {
        "project_id": str(valid_project.project_id),
        "name": valid_project.name,
        "object": str(valid_project.object),
        "project_leader": str(valid_project.project_leader),
        "night_shift_available": valid_project.night_shift_available,
        "extreme_conditions_available": valid_project.extreme_conditions_available,
        "created_by": str(valid_project.created_by),
        "created_at": valid_project.created_at,
        "deleted": valid_project.deleted,
    }
    invalid_record = {**valid_record, "project_id": str(uuid4()), "name": "   "}

    class FakeProjectsManager(ProjectsManager):
        def get_all_filtered_with_status(self, **_kwargs):
            return [invalid_record, valid_record]

    repository = SQLAlchemyProjectRepository(manager=FakeProjectsManager())

    result = repository.list_project_records(
        ProjectListQuery(),
        ProjectActor(role="admin", user_id=uuid4()),
    )

    assert result == [invalid_record, valid_record]


def test_project_repository_get_record_keeps_invalid_legacy_project():
    project_id = uuid4()
    invalid_record = {
        "project_id": str(project_id),
        "name": "   ",
        "object": str(uuid4()),
        "created_at": 1,
    }

    class FakeProjectsManager(ProjectsManager):
        def get_by_id(self, _project_id):
            return invalid_record

    repository = SQLAlchemyProjectRepository(manager=FakeProjectsManager())

    assert repository.get_project_record(project_id) == invalid_record
