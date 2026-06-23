from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum as PyEnum
from uuid import UUID

from .errors import LeaveValidationError
from .policies import LeavePeriod


class AbsenceReason(str, PyEnum):
    VACATION = "vacation"
    SICK_LEAVE = "sick_leave"
    DAY_OFF = "day_off"

    def label(self) -> str:
        return {
            "vacation": "Отпуск",
            "sick_leave": "Больничный",
            "day_off": "Отгул",
        }[self.value]


@dataclass(frozen=True, slots=True)
class Leave:
    leave_id: UUID
    start_date: int
    end_date: int
    reason: AbsenceReason
    user_id: UUID
    responsible_id: UUID
    created_by: UUID
    created_at: int
    comment: str | None = None
    updated_by: UUID | None = None
    updated_at: int | None = None
    deleted: bool = False
    _period: LeavePeriod = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.reason, AbsenceReason):
            raise LeaveValidationError("Leave reason must be an AbsenceReason value.")
        if not isinstance(self.deleted, bool):
            raise LeaveValidationError("Leave deleted flag must be a boolean.")

        period = LeavePeriod(self.start_date, self.end_date)
        object.__setattr__(self, "_period", period)

    @property
    def period(self) -> LeavePeriod:
        return self._period

    def mark_deleted(self, *, updated_by: UUID | None, updated_at: int) -> "Leave":
        return replace(self, deleted=True, updated_by=updated_by, updated_at=updated_at)

    def with_updates(self, **changes) -> "Leave":
        return replace(self, **changes)
