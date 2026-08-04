from uuid import uuid4

import pytest

from app.domain.measurement_units import MeasurementUnit, MeasurementUnitNotFoundError
from app.use_cases.measurement_units import (
    CreateMeasurementUnitCommand,
    CreateMeasurementUnitUseCase,
    DeleteMeasurementUnitUseCase,
    GetMeasurementUnitUseCase,
    UpdateMeasurementUnitCommand,
    UpdateMeasurementUnitUseCase,
)


class Repository:
    def __init__(self):
        self.item = None

    def create_measurement_unit(self, item: MeasurementUnit) -> MeasurementUnit:
        self.item = item
        return item

    def get_measurement_unit(self, item_id):
        return self.item if self.item and self.item.measurement_unit_id == item_id else None

    def update_measurement_unit(self, item: MeasurementUnit) -> MeasurementUnit:
        self.item = item
        return item

    def delete_measurement_unit(self, item_id):
        if self.item and self.item.measurement_unit_id == item_id:
            self.item = None
            return True
        return False

    def list_measurement_units(self, query):
        return [self.item] if self.item is not None else []


def test_measurement_unit_crud_use_cases():
    repository = Repository()
    created = CreateMeasurementUnitUseCase(repository).execute(
        CreateMeasurementUnitCommand(" м ", uuid4())
    )
    assert created.name == "м"
    updated = UpdateMeasurementUnitUseCase(repository).execute(
        UpdateMeasurementUnitCommand(created.measurement_unit_id, "шт.")
    )
    assert updated.name == "шт."
    assert GetMeasurementUnitUseCase(repository).execute(created.measurement_unit_id) == updated
    assert DeleteMeasurementUnitUseCase(repository).execute(created.measurement_unit_id)


def test_measurement_unit_get_rejects_unknown_id():
    with pytest.raises(MeasurementUnitNotFoundError):
        GetMeasurementUnitUseCase(Repository()).execute(uuid4())
