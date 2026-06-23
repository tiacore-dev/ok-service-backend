from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.leaves import Leave

from .dto import LeaveListQuery


class LeaveRepository(Protocol):
    def has_shift_conflict(
        self,
        user_id: UUID,
        start_date: int,
        end_date: int,
    ) -> bool: ...

    def has_overlapping_leave(
        self,
        user_id: UUID,
        start_date: int,
        end_date: int,
        exclude_id: UUID | None = None,
    ) -> bool: ...

    def create_leave(self, leave: Leave) -> Leave: ...

    def get_leave(self, leave_id: UUID) -> Leave | None: ...

    def update_leave(self, leave: Leave) -> Leave | None: ...

    def delete_leave(self, leave_id: UUID) -> bool: ...

    def list_leaves(self, query: LeaveListQuery) -> list[Leave]: ...

