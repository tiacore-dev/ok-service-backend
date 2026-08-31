from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WorkPlanActor:
    role: str


@dataclass(frozen=True, slots=True)
class CreateWorkPlanCommand:
    user_id: UUID | None
    date: date
    summ: Decimal
    description: str | None


@dataclass(frozen=True, slots=True)
class UpdateWorkPlanCommand:
    work_plan_id: UUID
    user_id: UUID | None = None
    user_id_is_set: bool = False
    date: date | None = None
    date_is_set: bool = False
    summ: Decimal | None = None
    summ_is_set: bool = False
    description: str | None = None
    description_is_set: bool = False


@dataclass(frozen=True, slots=True)
class WorkPlanListQuery:
    offset: int = 0
    limit: int | None = 1000
    sort_by: str = "date"
    sort_order: str = "asc"
    year: int | None = None
    user_id: UUID | None = None
    user_id_is_null: bool | None = None
    deleted: bool | None = False
