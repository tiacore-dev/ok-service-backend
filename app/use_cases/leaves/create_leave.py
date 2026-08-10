from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Callable
from uuid import UUID, uuid4

from app.domain.leaves import Leave, LeaveConflictError

from .dto import CreateLeaveCommand
from .ports import LeaveRepository


@dataclass(slots=True)
class CreateLeaveUseCase:
    repository: LeaveRepository
    clock: Callable[[], int] = field(default=lambda: int(time()), repr=False)
    id_factory: Callable[[], UUID] = field(default=uuid4, repr=False)

    def execute(self, command: CreateLeaveCommand) -> Leave:
        self._validate_availability(command)
        leave = Leave(
            leave_id=self._new_id(),
            start_date=command.start_date,
            end_date=command.end_date,
            reason=command.reason,
            user_id=command.user_id,
            responsible_id=command.responsible_id,
            created_by=command.created_by,
            created_at=self._now(),
            comment=command.comment,
        )
        return self.repository.create_leave(leave)

    def _validate_availability(self, command: CreateLeaveCommand) -> None:
        conflict = self.repository.get_open_shift_conflict(
            command.user_id, command.start_date, command.end_date
        )
        if conflict is not None:
            raise LeaveConflictError(
                "Shift exists within the specified period",
                detail={"conflict_type": "open_shift", "shift_report": conflict},
            )

        if self.repository.has_overlapping_leave(
            command.user_id, command.start_date, command.end_date
        ):
            raise LeaveConflictError("Leave overlaps with existing record")

    def _new_id(self) -> UUID:
        return self.id_factory()

    def _now(self) -> int:
        return self.clock()
