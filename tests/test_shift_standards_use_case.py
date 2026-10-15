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
