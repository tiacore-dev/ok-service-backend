from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .entities import AcceptanceStatus


@dataclass(frozen=True, slots=True)
class AcceptanceStatusHistory:
    id: UUID
    acceptance_id: UUID
    changed_at: int
    changed_by: UUID
    from_status: AcceptanceStatus
    to_status: AcceptanceStatus

    def __post_init__(self) -> None:
        object.__setattr__(self, "changed_at", int(self.changed_at))
