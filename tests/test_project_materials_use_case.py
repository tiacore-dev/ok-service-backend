from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain.project_materials import ProjectMaterial
from app.use_cases.project_materials import (
    CreateProjectMaterialCommand,
    CreateProjectMaterialUseCase,
    DeleteProjectMaterialUseCase,
    ProjectMaterialActor,
    UpdateProjectMaterialCommand,
    UpdateProjectMaterialUseCase,
)


class FakeProjectMaterialRepository:
    def __init__(self, project_material: ProjectMaterial | None = None):
        self.project_material = project_material
        self.created = None
        self.updated = None
        self.owned_project_ids: list[UUID] | None = None

    def create_project_material(self, project_material: ProjectMaterial) -> ProjectMaterial:
        self.created = project_material
        self.project_material = project_material
        return project_material

    def get_project_material(self, project_material_id):
        if self.project_material and self.project_material.project_material_id == project_material_id:
            return self.project_material
        return None

    def update_project_material(self, project_material: ProjectMaterial):
        self.updated = project_material
        self.project_material = project_material
        return project_material

    def delete_project_material(self, project_material_id):
        return self.project_material is not None and self.project_material.project_material_id == project_material_id

    def list_project_materials(self, query):
        return [self.project_material] if self.project_material is not None else []

    def get_project_ids_by_leader(self, user_id):
        if self.owned_project_ids is not None:
            return self.owned_project_ids
        return [self.project_material.project] if self.project_material else []


def test_create_project_material_use_case():
    repository = FakeProjectMaterialRepository()
    command = CreateProjectMaterialCommand(
        project=uuid4(),
        material=uuid4(),
        quantity=Decimal("3.25"),
        created_by=uuid4(),
    )

    result = CreateProjectMaterialUseCase(repository=repository).execute(
        command, ProjectMaterialActor(role="admin", user_id=command.created_by)
    )

    assert result == repository.created
    assert result.quantity == Decimal("3.25")


def test_project_leader_can_create_material_in_own_project():
    repository = FakeProjectMaterialRepository()
    leader_id = uuid4()
    project_id = uuid4()
    repository.project_material = ProjectMaterial(
        project_material_id=uuid4(), project=project_id, material=uuid4(),
        quantity=Decimal("1"), created_by=leader_id, created_at=1,
    )
    command = CreateProjectMaterialCommand(
        project=project_id, material=uuid4(), quantity=Decimal("2"), created_by=leader_id
    )

    result = CreateProjectMaterialUseCase(repository=repository).execute(
        command, ProjectMaterialActor(role="project-leader", user_id=leader_id)
    )

    assert result.project == project_id


def test_project_leader_cannot_create_material_in_foreign_project():
    from app.domain.project_materials import ProjectMaterialForbiddenError

    repository = FakeProjectMaterialRepository()
    leader_id = uuid4()
    command = CreateProjectMaterialCommand(
        project=uuid4(), material=uuid4(), quantity=Decimal("2"), created_by=leader_id
    )

    with pytest.raises(ProjectMaterialForbiddenError):
        CreateProjectMaterialUseCase(repository=repository).execute(
            command, ProjectMaterialActor(role="project-leader", user_id=leader_id)
        )


def test_update_project_material_use_case():
    project_material = ProjectMaterial(
        project_material_id=uuid4(),
        project=uuid4(),
        material=uuid4(),
        quantity=Decimal("3.25"),
        created_by=uuid4(),
        created_at=1,
    )
    repository = FakeProjectMaterialRepository(project_material)

    result = UpdateProjectMaterialUseCase(repository=repository).execute(
        UpdateProjectMaterialCommand(
            project_material_id=project_material.project_material_id,
            quantity=Decimal("6.0"),
            quantity_is_set=True,
        ), ProjectMaterialActor(role="admin", user_id=uuid4())
    )

    assert result.quantity == Decimal("6.0")


def test_update_project_material_use_case_clears_optional_field():
    project_material = ProjectMaterial(
        project_material_id=uuid4(),
        project=uuid4(),
        material=uuid4(),
        quantity=Decimal("3.25"),
        created_by=uuid4(),
        created_at=1,
        project_work=uuid4(),
    )
    repository = FakeProjectMaterialRepository(project_material)

    result = UpdateProjectMaterialUseCase(repository=repository).execute(
        UpdateProjectMaterialCommand(
            project_material_id=project_material.project_material_id,
            project_work=None,
            project_work_is_set=True,
        ), ProjectMaterialActor(role="admin", user_id=uuid4())
    )

    assert result.project_work is None


def test_project_leader_can_edit_and_delete_material_in_own_project():
    leader_id = uuid4()
    project_material = ProjectMaterial(
        project_material_id=uuid4(), project=uuid4(), material=uuid4(),
        quantity=Decimal("1"), created_by=leader_id, created_at=1,
    )
    repository = FakeProjectMaterialRepository(project_material)
    actor = ProjectMaterialActor(role="project-leader", user_id=leader_id)

    edited = UpdateProjectMaterialUseCase(repository).execute(
        UpdateProjectMaterialCommand(
            project_material_id=project_material.project_material_id,
            quantity=Decimal("4"), quantity_is_set=True,
        ), actor
    )

    assert edited.quantity == Decimal("4")
    assert DeleteProjectMaterialUseCase(repository).execute(
        project_material.project_material_id, actor
    )


def test_project_leader_cannot_edit_or_delete_foreign_material():
    leader_id = uuid4()
    project_material = ProjectMaterial(
        project_material_id=uuid4(), project=uuid4(), material=uuid4(),
        quantity=Decimal("1"), created_by=uuid4(), created_at=1,
    )
    repository = FakeProjectMaterialRepository(project_material)
    repository.owned_project_ids = []
    actor = ProjectMaterialActor(role="project-leader", user_id=leader_id)
    from app.domain.project_materials import ProjectMaterialForbiddenError

    with pytest.raises(ProjectMaterialForbiddenError):
        UpdateProjectMaterialUseCase(repository).execute(
            UpdateProjectMaterialCommand(
                project_material_id=project_material.project_material_id,
                quantity=Decimal("4"), quantity_is_set=True,
            ), actor
        )
    with pytest.raises(ProjectMaterialForbiddenError):
        DeleteProjectMaterialUseCase(repository).execute(
            project_material.project_material_id, actor
        )
