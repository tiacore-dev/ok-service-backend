from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.work_plans import WorkPlan

from .dto import WorkPlanListQuery


class WorkPlanRepository(Protocol):
    def create_work_plan(self, work_plan: WorkPlan) -> WorkPlan: ...

    def get_work_plan(self, work_plan_id: UUID) -> WorkPlan | None: ...

    def update_work_plan(self, work_plan: WorkPlan) -> WorkPlan | None: ...

    def delete_work_plan(self, work_plan_id: UUID) -> bool: ...

    def list_work_plans(self, query: WorkPlanListQuery) -> list[WorkPlan]: ...
