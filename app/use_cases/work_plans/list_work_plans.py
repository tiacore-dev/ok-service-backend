from dataclasses import dataclass

from app.domain.work_plans import WorkPlan

from .dto import WorkPlanListQuery
from .ports import WorkPlanRepository


@dataclass(slots=True)
class ListWorkPlansUseCase:
    repository: WorkPlanRepository

    def execute(self, query: WorkPlanListQuery) -> list[WorkPlan]:
        return self.repository.list_work_plans(query)
