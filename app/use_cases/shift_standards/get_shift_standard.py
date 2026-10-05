from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_standards import ShiftStandardNotFoundError

from .ports import ShiftStandardRepository


@dataclass(slots=True)
class GetShiftStandardUseCase:
    repository: ShiftStandardRepository

    def execute(self, item_id: UUID):
        item = self.repository.get_shift_standard(item_id)
        if item is None:
            raise ShiftStandardNotFoundError("Shift standard not found")
        return item
