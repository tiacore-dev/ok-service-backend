from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.positions import PositionNotFoundError

from .ports import PositionRepository


@dataclass(slots=True)
class DeletePositionUseCase:
    repository: PositionRepository

    def execute(self, position_id: UUID) -> bool:
        current = self.repository.get_position(position_id)
        if current is None:
            raise PositionNotFoundError("Position not found")
        deleted = self.repository.delete_position(position_id)
        if not deleted:
            raise PositionNotFoundError("Position not found")
        return deleted
