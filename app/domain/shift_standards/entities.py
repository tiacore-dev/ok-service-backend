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
    production_rate_rub: float | None = None
    penalty_rate_percent: float | None = None

    def __post_init__(self) -> None:
        if isinstance(self.category, bool) or not isinstance(self.category, int):
            raise ShiftStandardValidationError("Shift standard category must be an integer.")
        if isinstance(self.standard, bool) or not isinstance(self.standard, (int, float)):
            raise ShiftStandardValidationError("Shift standard must be a number.")
        if not math.isfinite(float(self.standard)) or self.standard <= 0:
            raise ShiftStandardValidationError("Shift standard must be greater than zero.")
        if self.notification_text is not None and not isinstance(self.notification_text, str):
            raise ShiftStandardValidationError("Notification text must be a string or null.")
        for name in ("production_rate_rub", "penalty_rate_percent"):
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ShiftStandardValidationError(f"{name} must be a number or null.")
            if not math.isfinite(value) or value < 0:
                raise ShiftStandardValidationError(f"{name} must be a finite non-negative number.")
            if name == "penalty_rate_percent" and value > 100:
                raise ShiftStandardValidationError("penalty_rate_percent must not exceed 100.")
            object.__setattr__(self, name, float(value))
        object.__setattr__(self, "standard", float(self.standard))
        object.__setattr__(self, "created_at", int(self.created_at))

    def with_updates(self, **changes) -> "ShiftStandard":
        return replace(self, **changes)
