from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Callable

from app.domain.leaves import Leave, LeaveConflictError, LeaveNotFoundError

from .dto import UpdateLeaveCommand
from .ports import LeaveRepository


@dataclass(slots=True)
class UpdateLeaveUseCase:
    repository: LeaveRepository
    clock: Callable[[], int] = field(default=lambda: int(time()), repr=False)

    def execute(self, command: UpdateLeaveCommand) -> Leave:
        existing = self.repository.get_leave(command.leave_id)
        if existing is None:
            raise LeaveNotFoundError("Leave not found")

        next_start_date = command.start_date if command.start_date is not None else existing.start_date
        next_end_date = command.end_date if command.end_date is not None else existing.end_date
        next_user_id = command.user_id if command.user_id is not None else existing.user_id

        self._validate_availability(command, next_start_date, next_end_date, next_user_id)

        updated = existing.with_updates(
            start_date=next_start_date,
            end_date=next_end_date,
            reason=command.reason if command.reason is not None else existing.reason,
            user_id=next_user_id,
            responsible_id=(
                command.responsible_id
                if command.responsible_id is not None
                else existing.responsible_id
            ),
            comment=command.comment if command.comment is not None else existing.comment,
            updated_by=command.updated_by,
            updated_at=self._now(),
        )
        result = self.repository.update_leave(updated)
        if result is None:
            raise LeaveNotFoundError("Leave not found")
        return result

    def _validate_availability(
        self,
        command: UpdateLeaveCommand,
        start_date: int,
        end_date: int,
        user_id,
    ) -> None:
        if self.repository.has_shift_conflict(user_id, start_date, end_date):
            raise LeaveConflictError("Shift exists within the specified period")

        if self.repository.has_overlapping_leave(
            user_id, start_date, end_date, exclude_id=command.leave_id
        ):
            raise LeaveConflictError("Leave overlaps with existing record")

    def _now(self) -> int:
        return self.clock()
