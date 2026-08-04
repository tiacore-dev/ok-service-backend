from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result, require_uuid
from app.database.managers.works_managers import MeasurementUnitsManager
from app.domain.measurement_units import MeasurementUnit
from app.use_cases.measurement_units.dto import (
    MeasurementUnitListQuery,
)


def _entity(payload):
    return MeasurementUnit(
        measurement_unit_id=require_uuid(payload["measurement_unit_id"], "measurement_unit_id"),
        name=payload["name"], created_at=payload["created_at"],
        created_by=require_uuid(payload["created_by"], "created_by") if payload.get("created_by") else None,
    )


@dataclass(slots=True)
class SQLAlchemyMeasurementUnitRepository:
    manager: MeasurementUnitsManager = field(default_factory=MeasurementUnitsManager)

    def create_measurement_unit(self, item: MeasurementUnit) -> MeasurementUnit:
        return _entity(normalize_result(self.manager.add(name=item.name, created_by=item.created_by)))
    def get_measurement_unit(self, item_id: UUID) -> MeasurementUnit | None:
        record = normalize_result(self.manager.get_by_id(item_id))
        return _entity(record) if record else None
    def update_measurement_unit(self, item: MeasurementUnit) -> MeasurementUnit | None:
        record = normalize_result(self.manager.update(record_id=item.measurement_unit_id, name=item.name))
        return _entity(record) if record else None
    def delete_measurement_unit(self, item_id: UUID):
        return self.manager.delete(item_id) is not None
    def list_measurement_units(self, query: MeasurementUnitListQuery) -> list[MeasurementUnit]:
        return [_entity(record) for record in self.manager.get_all_filtered(offset=query.offset, limit=query.limit, name=query.name, sort_by="name", sort_order="asc")]
