from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.positions import Position, PositionNotFoundError

from .ports import PositionRepository


@dataclass(slots=True)
class GetPositionUseCase:
    repository: PositionRepository

    def execute(self, position_id: UUID) -> Position:
        position = self.repository.get_position(position_id)
        if position is None:
            raise PositionNotFoundError("Position not found")
        return position
