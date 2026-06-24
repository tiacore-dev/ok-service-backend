from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from app.domain.positions import Position, PositionNotFoundError, PositionValidationError
from app.use_cases.positions import (
    CreatePositionCommand,
    CreatePositionUseCase,
    DeletePositionUseCase,
    GetPositionUseCase,
    ListPositionsUseCase,
    PositionListQuery,
    UpdatePositionCommand,
    UpdatePositionUseCase,
)


@dataclass
class FakePositionRepository:
    position: Position | None = None
    created: Position | None = None
    updated: Position | None = None
    deleted: UUID | None = None
    listed_query: PositionListQuery | None = None

    def create_position(self, position: Position) -> Position:
        self.created = position
        self.position = position
        return position

    def get_position(self, position_id: UUID) -> Position | None:
        return (
            self.position
            if self.position and self.position.position_id == position_id
            else None
        )

    def update_position(self, position: Position) -> Position | None:
        self.updated = position
        self.position = position
        return position

    def delete_position(self, position_id: UUID) -> bool:
        self.deleted = position_id
        return self.position is not None and self.position.position_id == position_id

    def list_positions(self, query: PositionListQuery) -> list[Position]:
        self.listed_query = query
        return [self.position] if self.position is not None else []


def _position() -> Position:
    return Position(
        position_id=uuid4(),
        name="Engineer",
        created_by=uuid4(),
        created_at=1,
    )


def test_position_domain_trims_name():
    position = Position(
        position_id=uuid4(),
        name="  Foreman  ",
        created_by=uuid4(),
        created_at=1,
    )

    assert position.name == "Foreman"


def test_position_domain_rejects_blank_name():
    with pytest.raises(PositionValidationError):
        Position(position_id=uuid4(), name="   ", created_by=uuid4(), created_at=1)


def test_create_position_use_case_persists_entity():
    repository = FakePositionRepository()
    command = CreatePositionCommand(name="Planner", created_by=uuid4())

    result = CreatePositionUseCase(repository=repository).execute(command)

    assert result == repository.created
    assert result.name == "Planner"


def test_get_position_use_case_returns_record():
    position = _position()
    repository = FakePositionRepository(position=position)

    result = GetPositionUseCase(repository=repository).execute(position.position_id)

    assert result == position


def test_update_position_use_case_updates_name():
    position = _position()
    repository = FakePositionRepository(position=position)

    result = UpdatePositionUseCase(repository=repository).execute(
        UpdatePositionCommand(position_id=position.position_id, name="Supervisor")
    )

    assert result.name == "Supervisor"
    assert repository.updated is not None


def test_update_position_use_case_rejects_missing_record():
    repository = FakePositionRepository()

    with pytest.raises(PositionNotFoundError):
        UpdatePositionUseCase(repository=repository).execute(
            UpdatePositionCommand(position_id=uuid4(), name="Supervisor")
        )


def test_delete_position_use_case_requires_existing_record():
    repository = FakePositionRepository()

    with pytest.raises(PositionNotFoundError):
        DeletePositionUseCase(repository=repository).execute(uuid4())


def test_list_positions_use_case_delegates():
    position = _position()
    repository = FakePositionRepository(position=position)
    query = PositionListQuery(name="Eng")

    result = ListPositionsUseCase(repository=repository).execute(query)

    assert result == [position]
    assert repository.listed_query == query
