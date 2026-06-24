from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProjectSchedule:
    project_schedule_id: UUID
    project: UUID
    work: UUID
    quantity: float
    created_by: UUID
    created_at: int
    date: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantity", float(self.quantity))
        object.__setattr__(self, "created_at", int(self.created_at))
        if self.date is not None:
            object.__setattr__(self, "date", int(self.date))

    def with_updates(
        self,
        *,
        project: UUID | None = None,
        work: UUID | None = None,
        quantity: float | Decimal | None = None,
        date: int | None = None,
    ) -> "ProjectSchedule":
        return replace(
            self,
            project=self.project if project is None else project,
            work=self.work if work is None else work,
            quantity=self.quantity if quantity is None else float(quantity),
            date=self.date if date is None else date,
        )
