from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.shift_report_materials import ShiftReportMaterial
from app.use_cases.shift_report_materials import (
    CreateShiftReportMaterialCommand,
    CreateShiftReportMaterialUseCase,
    ShiftReportMaterialListQuery,
    UpdateShiftReportMaterialCommand,
    UpdateShiftReportMaterialUseCase,
)


class FakeRepository:
    def __init__(self, material: ShiftReportMaterial | None = None):
        self.material = material
        self.created = None
        self.updated = None

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


def test_create_shift_report_material_use_case():
    repository = FakeRepository()
    command = CreateShiftReportMaterialCommand(
        shift_report=uuid4(),
        material=uuid4(),
        quantity=Decimal("3.25"),
        created_by=uuid4(),
    )

    result = CreateShiftReportMaterialUseCase(repository=repository).execute(command)

    assert result.quantity == Decimal("3.25")
    assert repository.created is not None


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
