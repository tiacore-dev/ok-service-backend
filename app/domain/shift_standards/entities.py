import math
from dataclasses import dataclass, replace
from uuid import UUID

from .errors import ShiftStandardValidationError


@dataclass(frozen=True, slots=True)
class ShiftStandard:
    shift_standard_id: UUID
    category: int
    standard: float
    notification_text: str | None
    created_at: int
    created_by: UUID

    def __post_init__(self) -> None:
        if isinstance(self.category, bool) or not isinstance(self.category, int):
            raise ShiftStandardValidationError("Shift standard category must be an integer.")
        if isinstance(self.standard, bool) or not isinstance(self.standard, (int, float)):
            raise ShiftStandardValidationError("Shift standard must be a number.")
        if not math.isfinite(float(self.standard)) or self.standard <= 0:
            raise ShiftStandardValidationError("Shift standard must be greater than zero.")
        if self.notification_text is not None and not isinstance(self.notification_text, str):
            raise ShiftStandardValidationError("Notification text must be a string or null.")
        object.__setattr__(self, "standard", float(self.standard))
        object.__setattr__(self, "created_at", int(self.created_at))

    def with_updates(self, **changes) -> "ShiftStandard":
        return replace(self, **changes)
