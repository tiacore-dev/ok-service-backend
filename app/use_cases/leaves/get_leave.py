from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.leaves import Leave, LeaveNotFoundError

from .ports import LeaveRepository


@dataclass(slots=True)
class GetLeaveUseCase:
    repository: LeaveRepository

    def execute(self, leave_id: UUID) -> Leave:
        leave = self.repository.get_leave(leave_id)
        if leave is None:
            raise LeaveNotFoundError("Leave not found")
        return leave

