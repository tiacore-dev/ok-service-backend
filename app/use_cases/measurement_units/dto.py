from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.measurement_units import MeasurementUnit


@dataclass(frozen=True, slots=True)
class CreateMeasurementUnitCommand:
    name: str
    created_by: UUID


@dataclass(frozen=True, slots=True)
class UpdateMeasurementUnitCommand:
    measurement_unit_id: UUID
    name: str | None = None


@dataclass(frozen=True, slots=True)
class MeasurementUnitListQuery:
    offset: int = 0
    limit: int | None = 1000
    name: str | None = None


class MeasurementUnitRepository(Protocol):
    def create_measurement_unit(self, item: MeasurementUnit) -> MeasurementUnit: ...
    def get_measurement_unit(self, item_id: UUID) -> MeasurementUnit | None: ...
    def update_measurement_unit(self, item: MeasurementUnit) -> MeasurementUnit | None: ...
    def delete_measurement_unit(self, item_id: UUID) -> bool: ...
    def list_measurement_units(self, query: MeasurementUnitListQuery) -> list[MeasurementUnit]: ...
