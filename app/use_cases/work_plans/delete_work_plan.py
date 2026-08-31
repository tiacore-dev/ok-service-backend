from dataclasses import dataclass
from uuid import UUID

from app.domain.work_plans import (
    WorkPlan,
    WorkPlanForbiddenError,
    WorkPlanNotFoundError,
)

from .dto import WorkPlanActor
from .ports import WorkPlanRepository


@dataclass(slots=True)
class SoftDeleteWorkPlanUseCase:
    repository: WorkPlanRepository

    def execute(self, work_plan_id: UUID, actor: WorkPlanActor) -> WorkPlan:
        if actor.role not in {"admin", "manager"}:
            raise WorkPlanForbiddenError("Forbidden")
        current = self.repository.get_work_plan(work_plan_id)
        if current is None:
            raise WorkPlanNotFoundError("Work plan not found")
        result = self.repository.update_work_plan(current.with_updates(deleted=True))
        if result is None:
            raise WorkPlanNotFoundError("Work plan not found")
        return result


@dataclass(slots=True)
class DeleteWorkPlanUseCase:
    repository: WorkPlanRepository

    def execute(self, work_plan_id: UUID, actor: WorkPlanActor) -> bool:
        if actor.role not in {"admin", "manager"}:
            raise WorkPlanForbiddenError("Forbidden")
        if self.repository.get_work_plan(work_plan_id) is None:
            raise WorkPlanNotFoundError("Work plan not found")
        if not self.repository.delete_work_plan(work_plan_id):
            raise WorkPlanNotFoundError("Work plan not found")
        return True
