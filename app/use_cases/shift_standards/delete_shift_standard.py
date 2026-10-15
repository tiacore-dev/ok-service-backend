from dataclasses import dataclass
from uuid import UUID

from app.domain.shift_standards import ShiftStandardNotFoundError

from .ports import ShiftStandardRepository


@dataclass(slots=True)
class DeleteShiftStandardUseCase:
    repository: ShiftStandardRepository

    def execute(self, item_id: UUID) -> bool:
        if not self.repository.delete_shift_standard(item_id):
            raise ShiftStandardNotFoundError("Shift standard not found")
        return True
