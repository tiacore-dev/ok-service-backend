from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.positions_manager import PositionsManager
from app.domain.positions import Position
from app.use_cases.positions.dto import PositionListQuery
from app.use_cases.positions.ports import PositionRepository

from .mappers import position_dict_to_entity, position_entity_to_create_payload


@dataclass(slots=True)
class SQLAlchemyPositionRepository(PositionRepository):
    manager: PositionsManager = field(default_factory=PositionsManager)

    def create_position(self, position: Position) -> Position:
        created = self.manager.add(**position_entity_to_create_payload(position))
        record = normalize_result(created)
        if record is None:
            raise ValueError("Position creation did not return a record")
        return position_dict_to_entity(record)

    def get_position(self, position_id: UUID) -> Position | None:
        record = normalize_result(self.manager.get_by_id(position_id))
        if record is None:
            return None
        return position_dict_to_entity(record)

    def update_position(self, position: Position) -> Position | None:
        updated = self.manager.update(
            record_id=position.position_id,
            name=position.name,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return position_dict_to_entity(record)

    def delete_position(self, position_id: UUID) -> bool:
        deleted = self.manager.delete(record_id=position_id)
        return deleted is not None

    def list_positions(self, query: PositionListQuery) -> list[Position]:
        if query.sort_by is None:
            records = self.manager.get_all_filtered(
                offset=query.offset,
                limit=query.limit,
                sort_order=query.sort_order,
                name=query.name,
            )
        else:
            records = self.manager.get_all_filtered(
                offset=query.offset,
                limit=query.limit,
                sort_by=query.sort_by,
                sort_order=query.sort_order,
                name=query.name,
            )
        return [position_dict_to_entity(record) for record in records]
