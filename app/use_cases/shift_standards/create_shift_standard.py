from dataclasses import dataclass
from uuid import uuid4

from app.domain.shift_standards import ShiftStandard
from app.use_cases.time_utils import utc_epoch_milliseconds

from .dto import CreateShiftStandardCommand
from .ports import ShiftStandardRepository


@dataclass(slots=True)
class CreateShiftStandardUseCase:
    repository: ShiftStandardRepository

    def execute(self, command: CreateShiftStandardCommand) -> ShiftStandard:
        return self.repository.create_shift_standard(
            ShiftStandard(
                shift_standard_id=uuid4(),
                category=command.category,
                standard=command.standard,
                notification_text=command.notification_text,
                created_at=utc_epoch_milliseconds(),
                created_by=command.created_by,
            )
        )
