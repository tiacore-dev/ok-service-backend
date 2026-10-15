from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateShiftStandardCommand:
    category: int
    standard: float
    notification_text: str | None
    created_by: UUID


@dataclass(frozen=True, slots=True)
class UpdateShiftStandardCommand:
    shift_standard_id: UUID
    category: int | None = None
    standard: float | None = None
    notification_text: str | None = None
    notification_text_provided: bool = False


@dataclass(frozen=True, slots=True)
class ShiftStandardListQuery:
    offset: int = 0
    limit: int | None = 1000
    category: int | None = None

