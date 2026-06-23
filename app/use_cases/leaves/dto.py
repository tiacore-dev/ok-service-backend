from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.leaves import AbsenceReason


@dataclass(frozen=True, slots=True)
class CreateLeaveCommand:
    start_date: int
    end_date: int
    reason: AbsenceReason
    user_id: UUID
    responsible_id: UUID
    created_by: UUID
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateLeaveCommand:
    leave_id: UUID
    updated_by: UUID
    start_date: int | None = None
    end_date: int | None = None
    reason: AbsenceReason | None = None
    user_id: UUID | None = None
    responsible_id: UUID | None = None
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class LeaveListQuery:
    offset: int = 0
    limit: int | None = 1000
    sort_by: str = "created_at"
    sort_order: str = "desc"
    user_id: UUID | None = None
    responsible_id: UUID | None = None
    reason: AbsenceReason | None = None
    date_from: int | None = None
    date_to: int | None = None
    deleted: bool | None = None


@dataclass(frozen=True, slots=True)
class AbsenceReasonDTO:
    reason_id: str
    name: str

