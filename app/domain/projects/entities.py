from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from .errors import ProjectValidationError
from .statuses import ProjectStatus


@dataclass(frozen=True, slots=True)
class Project:
    project_id: UUID
    name: str
    object: UUID
    project_leader: UUID | None
    night_shift_available: bool
    extreme_conditions_available: bool
    created_by: UUID | None
    created_at: int
    deleted: bool = False
    status: ProjectStatus = ProjectStatus.PENDING

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "created_at", int(self.created_at))
        object.__setattr__(self, "deleted", bool(self.deleted))
        object.__setattr__(self, "status", ProjectStatus(self.status))
        object.__setattr__(self, "night_shift_available", bool(self.night_shift_available))
        object.__setattr__(
            self,
            "extreme_conditions_available",
            bool(self.extreme_conditions_available),
        )
        if not self.name:
            raise ProjectValidationError("Project name is required.")

    def with_updates(
        self,
        *,
        name: str | None = None,
        object: UUID | None = None,
        project_leader: UUID | None = None,
        night_shift_available: bool | None = None,
        extreme_conditions_available: bool | None = None,
        deleted: bool | None = None,
        status: ProjectStatus | None = None,
    ) -> "Project":
        return replace(
            self,
            name=self.name if name is None else name,
            object=self.object if object is None else object,
            project_leader=self.project_leader
            if project_leader is None
            else project_leader,
            night_shift_available=self.night_shift_available
            if night_shift_available is None
            else night_shift_available,
            extreme_conditions_available=self.extreme_conditions_available
            if extreme_conditions_available is None
            else extreme_conditions_available,
            deleted=self.deleted if deleted is None else deleted,
            status=self.status if status is None else status,
        )
