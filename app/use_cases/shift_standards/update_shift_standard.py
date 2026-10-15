from dataclasses import dataclass

from app.domain.shift_standards import ShiftStandardNotFoundError

from .dto import UpdateShiftStandardCommand
from .ports import ShiftStandardRepository


@dataclass(slots=True)
class UpdateShiftStandardUseCase:
    repository: ShiftStandardRepository

    def execute(self, command: UpdateShiftStandardCommand):
        existing = self.repository.get_shift_standard(command.shift_standard_id)
        if existing is None:
            raise ShiftStandardNotFoundError("Shift standard not found")
        changes = {}
        if command.category is not None:
            changes["category"] = command.category
        if command.standard is not None:
            changes["standard"] = command.standard
        if command.notification_text_provided:
            changes["notification_text"] = command.notification_text
        if not changes:
            return existing
        result = self.repository.update_shift_standard(existing.with_updates(**changes))
        if result is None:
            raise ShiftStandardNotFoundError("Shift standard not found")
        return result
