from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.shift_report_materials import ShiftReportMaterial
from app.use_cases.shift_report_materials import (
    CreateShiftReportMaterialCommand,
    CreateShiftReportMaterialUseCase,
    ShiftReportMaterialActor,
    ShiftReportMaterialListQuery,
    UpdateShiftReportMaterialCommand,
    UpdateShiftReportMaterialUseCase,
)


class FakeRepository:
    def __init__(self, material: ShiftReportMaterial | None = None):
        self.material = material
        self.created = None
        self.updated = None
        self.shift_report_context: tuple[UUID, UUID | None, bool] | None = None

    def create_shift_report_material(
        self, shift_report_material: ShiftReportMaterial
    ) -> ShiftReportMaterial:
        self.created = shift_report_material
        self.material = shift_report_material
        return shift_report_material

    def get_shift_report_material(self, shift_report_material_id: UUID):
        if (
            self.material
            and self.material.shift_report_material_id == shift_report_material_id
        ):
            return self.material
        return None

    def update_shift_report_material(
        self, shift_report_material: ShiftReportMaterial
    ) -> ShiftReportMaterial | None:
        self.updated = shift_report_material
        self.material = shift_report_material
        return shift_report_material

    def delete_shift_report_material(self, shift_report_material_id: UUID) -> bool:
        return (
            self.material is not None
            and self.material.shift_report_material_id == shift_report_material_id
        )

    def list_shift_report_materials(
        self, query: ShiftReportMaterialListQuery
    ) -> list[ShiftReportMaterial]:
        return [self.material] if self.material is not None else []

    def get_shift_report_context(self, shift_report_id):
        return self.shift_report_context


def test_create_shift_report_material_use_case():
    repository = FakeRepository()
    command = CreateShiftReportMaterialCommand(
        shift_report=uuid4(),
        material=uuid4(),
        quantity=Decimal("3.25"),
        created_by=uuid4(),
    )

    result = CreateShiftReportMaterialUseCase(repository=repository).execute(
        command, ShiftReportMaterialActor(role="admin", user_id=command.created_by)
    )

    assert result.quantity == Decimal("3.25")
    assert repository.created is not None


def test_project_leader_can_add_material_to_shift_in_own_project():
    repository = FakeRepository()
    leader_id = uuid4()
    repository.shift_report_context = (uuid4(), leader_id, False)
    command = CreateShiftReportMaterialCommand(
        shift_report=uuid4(), material=uuid4(), quantity=Decimal("3.25"), created_by=leader_id
    )

    result = CreateShiftReportMaterialUseCase(repository=repository).execute(
        command, ShiftReportMaterialActor(role="project-leader", user_id=leader_id)
    )

    assert result.quantity == Decimal("3.25")


def test_project_leader_cannot_add_material_to_foreign_project_shift():
    import pytest
    from app.domain.shift_report_materials import ShiftReportMaterialForbiddenError

    repository = FakeRepository()
    repository.shift_report_context = (uuid4(), uuid4(), False)
    leader_id = uuid4()
    command = CreateShiftReportMaterialCommand(
        shift_report=uuid4(), material=uuid4(), quantity=Decimal("1"), created_by=leader_id
    )

    with pytest.raises(ShiftReportMaterialForbiddenError):
        CreateShiftReportMaterialUseCase(repository=repository).execute(
            command, ShiftReportMaterialActor(role="project-leader", user_id=leader_id)
        )


def test_update_shift_report_material_use_case():
    existing_shift_report_material = ShiftReportMaterial(
        shift_report_material_id=uuid4(),
        shift_report=uuid4(),
        material=uuid4(),
        quantity=Decimal("1.00"),
        created_by=uuid4(),
        created_at=1,
    )
    repository = FakeRepository(material=existing_shift_report_material)

    result = UpdateShiftReportMaterialUseCase(repository=repository).execute(
        UpdateShiftReportMaterialCommand(
            shift_report_material_id=existing_shift_report_material.shift_report_material_id,
            quantity=Decimal("2.50"),
        )
    )

    assert result.quantity == Decimal("2.50")
