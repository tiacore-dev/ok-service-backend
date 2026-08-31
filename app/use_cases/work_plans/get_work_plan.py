from dataclasses import dataclass
from uuid import UUID

from app.domain.work_plans import WorkPlan, WorkPlanNotFoundError

from .ports import WorkPlanRepository


@dataclass(slots=True)
class GetWorkPlanUseCase:
    repository: WorkPlanRepository

    def execute(self, work_plan_id: UUID) -> WorkPlan:
        result = self.repository.get_work_plan(work_plan_id)
        if result is None:
            raise WorkPlanNotFoundError("Work plan not found")
        return result
