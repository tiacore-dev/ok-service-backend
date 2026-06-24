from uuid import UUID, uuid4

from app.domain.materials import Material
from app.use_cases.materials import (
    CreateMaterialCommand,
    CreateMaterialUseCase,
    MaterialListQuery,
    UpdateMaterialCommand,
    UpdateMaterialUseCase,
)


class FakeRepository:
    def __init__(self, material: Material | None = None):
        self.material = material
        self.created = None
        self.updated = None

    def create_material(self, material: Material) -> Material:
        self.created = material
        self.material = material
        return material

    def get_material(self, material_id: UUID) -> Material | None:
        if self.material and self.material.material_id == material_id:
            return self.material
        return None

    def update_material(self, material: Material) -> Material | None:
        self.updated = material
        self.material = material
        return material

    def delete_material(self, material_id: UUID) -> bool:
        return self.material is not None and self.material.material_id == material_id

    def list_materials(self, query: MaterialListQuery) -> list[Material]:
        return [self.material] if self.material is not None else []


def test_create_material_use_case():
    repository = FakeRepository()
    command = CreateMaterialCommand(
        name="Sand",
        measurement_unit="kg",
        created_by=uuid4(),
    )

    result = CreateMaterialUseCase(repository=repository).execute(command)

    assert result.name == "Sand"
    assert repository.created is not None


def test_update_material_use_case():
    existing_material = Material(
        material_id=uuid4(),
        name="Sand",
        measurement_unit="kg",
        created_by=uuid4(),
        created_at=1,
    )
    repository = FakeRepository(material=existing_material)

    result = UpdateMaterialUseCase(repository=repository).execute(
        UpdateMaterialCommand(
            material_id=existing_material.material_id,
            name="Gravel",
            deleted=True,
        )
    )

    assert result.name == "Gravel"
    assert result.deleted is True
