from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateShiftStandardCommand:
    category: int
    standard: float
    notification_text: str | None
    created_by: UUID
    production_rate_rub: float | None = None
    penalty_rate_percent: float | None = None


@dataclass(frozen=True, slots=True)
class UpdateShiftStandardCommand:
    shift_standard_id: UUID
    category: int | None = None
    standard: float | None = None
    notification_text: str | None = None
    notification_text_provided: bool = False
    production_rate_rub: float | None = None
    production_rate_rub_provided: bool = False
    penalty_rate_percent: float | None = None
    penalty_rate_percent_provided: bool = False


@dataclass(frozen=True, slots=True)
class ShiftStandardListQuery:
    offset: int = 0
    limit: int | None = 1000
    category: int | None = None

