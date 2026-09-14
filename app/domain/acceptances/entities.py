from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from uuid import UUID

from .errors import AcceptanceValidationError


class AcceptanceStatus(str, Enum):
    PRESENTED = "presented"
    VIOLATIONS_FOUND = "violations_found"
    ACCEPTED_ON_SITE = "accepted_on_site"
    DOCUMENTS_SIGNED = "documents_signed"


@dataclass(frozen=True, slots=True)
class Acceptance:
    id: UUID
    date: int
    project_id: UUID
    status: AcceptanceStatus
    comment: str | None = None

    def __post_init__(self) -> None:
        if self.date < 0:
            raise AcceptanceValidationError("Acceptance date must be non-negative.")
        object.__setattr__(self, "date", int(self.date))
        object.__setattr__(self, "status", AcceptanceStatus(self.status))

    def with_updates(self, **changes) -> "Acceptance":
        return replace(self, **changes)
