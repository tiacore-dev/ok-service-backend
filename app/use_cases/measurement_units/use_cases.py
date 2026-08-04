from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from app.domain.measurement_units import MeasurementUnit, MeasurementUnitNotFoundError
from app.use_cases.time_utils import utc_epoch_seconds

from .dto import (
    CreateMeasurementUnitCommand,
    MeasurementUnitListQuery,
    MeasurementUnitRepository,
    UpdateMeasurementUnitCommand,
)


@dataclass(slots=True)
class CreateMeasurementUnitUseCase:
    repository: MeasurementUnitRepository
    def execute(self, command: CreateMeasurementUnitCommand) -> MeasurementUnit:
        return self.repository.create_measurement_unit(MeasurementUnit(uuid4(), command.name, utc_epoch_seconds(), command.created_by))


@dataclass(slots=True)
class GetMeasurementUnitUseCase:
    repository: MeasurementUnitRepository
    def execute(self, item_id: UUID) -> MeasurementUnit:
        item = self.repository.get_measurement_unit(item_id)
        if item is None:
            raise MeasurementUnitNotFoundError("Measurement unit not found")
        return item


@dataclass(slots=True)
class ListMeasurementUnitsUseCase:
    repository: MeasurementUnitRepository
    def execute(self, query: MeasurementUnitListQuery) -> list[MeasurementUnit]:
        return self.repository.list_measurement_units(query)


@dataclass(slots=True)
class UpdateMeasurementUnitUseCase:
    repository: MeasurementUnitRepository
    def execute(self, command: UpdateMeasurementUnitCommand) -> MeasurementUnit:
        item = self.repository.get_measurement_unit(command.measurement_unit_id)
        if item is None:
            raise MeasurementUnitNotFoundError("Measurement unit not found")
        if command.name is None:
            return item
        result = self.repository.update_measurement_unit(replace(item, name=command.name))
        if result is None:
            raise MeasurementUnitNotFoundError("Measurement unit not found")
        return result


@dataclass(slots=True)
class DeleteMeasurementUnitUseCase:
    repository: MeasurementUnitRepository
    def execute(self, item_id: UUID) -> bool:
        if not self.repository.delete_measurement_unit(item_id):
            raise MeasurementUnitNotFoundError("Measurement unit not found")
        return True
