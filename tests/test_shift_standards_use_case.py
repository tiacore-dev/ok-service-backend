from uuid import UUID, uuid4

import pytest

from app.domain.shift_standards import ShiftStandard, ShiftStandardValidationError
from app.use_cases.shift_standards import (
    CreateShiftStandardCommand,
    CreateShiftStandardUseCase,
    ShiftStandardListQuery,
    UpdateShiftStandardCommand,
    UpdateShiftStandardUseCase,
)


class Repository:
    def __init__(self):
        self.item: ShiftStandard | None = None

    def create_shift_standard(self, item: ShiftStandard) -> ShiftStandard:
        self.item = item
        return item

    def get_shift_standard(self, item_id: UUID) -> ShiftStandard | None:
        return self.item if self.item and self.item.shift_standard_id == item_id else None

    def update_shift_standard(self, item: ShiftStandard) -> ShiftStandard:
        self.item = item
        return item

    def delete_shift_standard(self, item_id: UUID) -> bool:
        if self.item is None or self.item.shift_standard_id != item_id:
            return False
        self.item = None
        return True

    def list_shift_standards(self, query: ShiftStandardListQuery) -> list[ShiftStandard]:
        if self.item is None:
            return []
        return [self.item]


def test_shift_standard_create_and_update_preserve_explicit_null():
    repository = Repository()
    item = CreateShiftStandardUseCase(repository).execute(
        CreateShiftStandardCommand(2, 8.5, "Too long", uuid4())
    )
    assert item.category == 2
    assert item.standard == 8.5

    updated = UpdateShiftStandardUseCase(repository).execute(
        UpdateShiftStandardCommand(item.shift_standard_id, notification_text=None, notification_text_provided=True)
    )
    assert updated.notification_text is None


def test_shift_standard_rejects_non_positive_standard():
    with pytest.raises(ShiftStandardValidationError):
        ShiftStandard(uuid4(), 1, 0, None, 1, uuid4())


def test_shift_standard_rejects_non_finite_standard():
    with pytest.raises(ShiftStandardValidationError):
        ShiftStandard(uuid4(), 1, float("inf"), None, 1, uuid4())


@pytest.mark.parametrize("name", ["production_rate_rub", "penalty_rate_percent"])
@pytest.mark.parametrize("value", [-0.01, float("inf"), float("-inf"), float("nan"), True, "1"])
def test_shift_standard_rejects_invalid_optional_rates(name, value):
    with pytest.raises(ShiftStandardValidationError):
        ShiftStandard(uuid4(), 1, 8, None, 1, uuid4(), **{name: value})


def test_shift_standard_rejects_penalty_above_100():
    with pytest.raises(ShiftStandardValidationError):
        ShiftStandard(uuid4(), 1, 8, None, 1, uuid4(), penalty_rate_percent=100.01)


@pytest.mark.parametrize("production,penalty", [(None, None), (0, 0), (1500.25, 100)])
def test_shift_standard_optional_rates_create_preserve_update_and_clear(production, penalty):
    repository = Repository()
    item = CreateShiftStandardUseCase(repository).execute(
        CreateShiftStandardCommand(
            2, 8.5, None, uuid4(),
            production_rate_rub=production, penalty_rate_percent=penalty,
        )
    )
    assert item.production_rate_rub == production
    assert item.penalty_rate_percent == penalty
    updated = UpdateShiftStandardUseCase(repository).execute(
        UpdateShiftStandardCommand(item.shift_standard_id, standard=9)
    )
    assert updated.production_rate_rub == production
    assert updated.penalty_rate_percent == penalty
    updated = UpdateShiftStandardUseCase(repository).execute(
        UpdateShiftStandardCommand(
            item.shift_standard_id,
            production_rate_rub=0, production_rate_rub_provided=True,
        )
    )
    assert updated.production_rate_rub == 0.0
    assert updated.penalty_rate_percent == penalty
    cleared = UpdateShiftStandardUseCase(repository).execute(
        UpdateShiftStandardCommand(
            item.shift_standard_id,
            production_rate_rub_provided=True, penalty_rate_percent_provided=True,
        )
    )
    assert cleared.production_rate_rub is None
    assert cleared.penalty_rate_percent is None
