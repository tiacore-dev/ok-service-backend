from __future__ import annotations

from dataclasses import dataclass

from .errors import LeaveValidationError


@dataclass(frozen=True, slots=True)
class LeavePeriod:
    start_date: int
    end_date: int

    def __post_init__(self) -> None:
        if not isinstance(self.start_date, int) or not isinstance(self.end_date, int):
            raise LeaveValidationError("Leave period boundaries must be integers.")
        if self.start_date > self.end_date:
            raise LeaveValidationError(
                "'start_date' must be less than or equal to 'end_date'."
            )

    def overlaps(self, other: "LeavePeriod") -> bool:
        return not (
            self.end_date < other.start_date or self.start_date > other.end_date
        )


def leave_periods_overlap(
    start_date: int,
    end_date: int,
    other_start_date: int,
    other_end_date: int,
) -> bool:
    return LeavePeriod(start_date, end_date).overlaps(
        LeavePeriod(other_start_date, other_end_date)
    )
