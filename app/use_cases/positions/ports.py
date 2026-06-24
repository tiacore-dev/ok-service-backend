from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.positions import Position

from .dto import PositionListQuery


class PositionRepository(Protocol):
    def create_position(self, position: Position) -> Position: ...

    def get_position(self, position_id: UUID) -> Position | None: ...

    def update_position(self, position: Position) -> Position | None: ...

    def delete_position(self, position_id: UUID) -> bool: ...

    def list_positions(self, query: PositionListQuery) -> list[Position]: ...
