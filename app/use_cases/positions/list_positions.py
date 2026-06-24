from __future__ import annotations

from dataclasses import dataclass

from app.domain.positions import Position

from .dto import PositionListQuery
from .ports import PositionRepository


@dataclass(slots=True)
class ListPositionsUseCase:
    repository: PositionRepository

    def execute(self, query: PositionListQuery) -> list[Position]:
        return self.repository.list_positions(query)
