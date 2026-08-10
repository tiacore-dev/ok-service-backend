from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.leaves_manager import LeavesManager
from app.domain.leaves import Leave
from app.use_cases.leaves.dto import LeaveListQuery
from app.use_cases.leaves.ports import LeaveRepository

from .mappers import (
    leave_dict_to_entity,
    leave_entity_to_create_payload,
)


@dataclass(slots=True)
class SQLAlchemyLeaveRepository(LeaveRepository):
    manager: LeavesManager = field(default_factory=LeavesManager)

    def get_open_shift_conflict(
        self,
        user_id: UUID,
        start_date: int,
        end_date: int,
    ) -> dict[str, object] | None:
        return self.manager.get_open_shift_conflict(user_id, start_date, end_date)

    def has_overlapping_leave(
        self,
        user_id: UUID,
        start_date: int,
        end_date: int,
        exclude_id: UUID | None = None,
    ) -> bool:
        return self.manager.has_overlapping_leave(
            user_id,
            start_date,
            end_date,
            exclude_id=exclude_id,
        )

    def create_leave(self, leave: Leave) -> Leave:
        created = self.manager.add_leave(**leave_entity_to_create_payload(leave))
        record = normalize_result(created)
        if record is None:
            raise ValueError("Leave creation did not return a record")
        return leave_dict_to_entity(record)

    def get_leave(self, leave_id: UUID) -> Leave | None:
        record = normalize_result(self.manager.get_by_id(leave_id))
        if record is None:
            return None
        return leave_dict_to_entity(record)

    def update_leave(self, leave: Leave) -> Leave | None:
        updated = self.manager.update_leave(
            leave.leave_id,
            start_date=leave.start_date,
            end_date=leave.end_date,
            reason=leave.reason,
            user_id=leave.user_id,
            responsible_id=leave.responsible_id,
            comment=leave.comment,
            updated_by=leave.updated_by,
            updated_at=leave.updated_at,
            deleted=leave.deleted,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return leave_dict_to_entity(record)

    def delete_leave(self, leave_id: UUID) -> bool:
        deleted = self.manager.delete_leave(leave_id)
        return deleted is not None

    def list_leaves(self, query: LeaveListQuery) -> list[Leave]:
        records = self.manager.list_leaves(
            offset=query.offset,
            limit=query.limit,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            user_id=query.user_id,
            responsible_id=query.responsible_id,
            reason=query.reason.value if query.reason else None,
            date_from=query.date_from,
            date_to=query.date_to,
            deleted=query.deleted,
        )
        return [leave_dict_to_entity(record) for record in records]
