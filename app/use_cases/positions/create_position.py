from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.domain.positions import Position
from app.use_cases.time_utils import utc_epoch_seconds

from .dto import CreatePositionCommand
from .ports import PositionRepository


@dataclass(slots=True)
class CreatePositionUseCase:
    repository: PositionRepository

    def execute(self, command: CreatePositionCommand) -> Position:
        position = Position(
            position_id=uuid4(),
            name=command.name,
            created_by=command.created_by,
            created_at=utc_epoch_seconds(),
        )
        return self.repository.create_position(position)
