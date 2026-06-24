from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from .errors import WorkCategoryValidationError


@dataclass(frozen=True, slots=True)
class WorkCategory:
    work_category_id: UUID
    name: str
    created_by: UUID
    created_at: int
    deleted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.deleted, bool):
            raise WorkCategoryValidationError("Work category deleted flag must be boolean.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise WorkCategoryValidationError(
                "Work category name must be a non-empty string."
            )
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "created_at", int(self.created_at))

    def with_updates(self, **changes) -> "WorkCategory":
        return replace(self, **changes)
