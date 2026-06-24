from __future__ import annotations

from dataclasses import dataclass

from app.domain.positions import Position, PositionNotFoundError

from .dto import UpdatePositionCommand
from .ports import PositionRepository


@dataclass(slots=True)
class UpdatePositionUseCase:
    repository: PositionRepository

    def execute(self, command: UpdatePositionCommand) -> Position:
        current = self.repository.get_position(command.position_id)
        if current is None:
            raise PositionNotFoundError("Position not found")
        if command.name is None:
            return current

        updated = self.repository.update_position(
            current.with_updates(name=command.name)
        )
        if updated is None:
            raise PositionNotFoundError("Position not found")
        return updated
