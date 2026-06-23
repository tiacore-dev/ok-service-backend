from decimal import Decimal
from uuid import uuid4

from app.domain.project_materials import ProjectMaterial
from app.use_cases.project_materials import (
    CreateProjectMaterialCommand,
    CreateProjectMaterialUseCase,
    UpdateProjectMaterialCommand,
    UpdateProjectMaterialUseCase,
)


class FakeProjectMaterialRepository:
    def __init__(self, project_material: ProjectMaterial | None = None):
        self.project_material = project_material
        self.created = None
        self.updated = None

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


def test_create_project_material_use_case():
    repository = FakeProjectMaterialRepository()
    command = CreateProjectMaterialCommand(
        project=uuid4(),
        material=uuid4(),
        quantity=Decimal("3.25"),
        created_by=uuid4(),
    )

    result = CreateProjectMaterialUseCase(repository=repository).execute(command)

    assert result == repository.created
    assert result.quantity == Decimal("3.25")


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
        )
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
        )
    )

    assert result.project_work is None
