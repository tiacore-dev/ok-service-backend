from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from .errors import WorkPlanValidationError


@dataclass(frozen=True, slots=True)
class WorkPlan:
    work_plan_id: UUID
    user_id: UUID | None
    date: date
    summ: Decimal
    description: str | None
    deleted: bool = False

    def __post_init__(self) -> None:
        if self.date.day != 1:
            raise WorkPlanValidationError("Work plan date must be the first day of a month.")
        try:
            summ = Decimal(str(self.summ))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise WorkPlanValidationError("Work plan summ must be a valid decimal.") from exc
        object.__setattr__(self, "summ", summ)
        if not self.summ.is_finite():
            raise WorkPlanValidationError("Work plan summ must be finite.")
        if self.summ < 0:
            raise WorkPlanValidationError("Work plan summ must be non-negative.")
        if int(self.summ.as_tuple().exponent) < -2:
            raise WorkPlanValidationError("Work plan summ must have at most two decimal places.")
        if self.summ > Decimal("9999999999.99"):
            raise WorkPlanValidationError("Work plan summ exceeds the maximum value.")
        object.__setattr__(self, "deleted", bool(self.deleted))

    def with_updates(self, **changes) -> "WorkPlan":
        return replace(self, **changes)
