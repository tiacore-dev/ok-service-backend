from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Callable
from uuid import UUID

from app.domain.leaves import LeaveNotFoundError

from .ports import LeaveRepository


@dataclass(slots=True)
class SoftDeleteLeaveUseCase:
    repository: LeaveRepository
    clock: Callable[[], int] = lambda: int(time())  # type: ignore[assignment]

    def execute(self, leave_id: UUID, updated_by: UUID) -> None:
        leave = self.repository.get_leave(leave_id)
        if leave is None:
            raise LeaveNotFoundError("Leave not found")

        deleted_leave = leave.mark_deleted(updated_by=updated_by, updated_at=self._now())
        if self.repository.update_leave(deleted_leave) is None:
            raise LeaveNotFoundError("Leave not found")

    def _now(self) -> int:
        return self.clock()


@dataclass(slots=True)
class HardDeleteLeaveUseCase:
    repository: LeaveRepository

    def execute(self, leave_id: UUID) -> None:
        if not self.repository.delete_leave(leave_id):
            raise LeaveNotFoundError("Leave not found")
