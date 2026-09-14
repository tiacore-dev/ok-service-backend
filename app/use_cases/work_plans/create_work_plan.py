from dataclasses import dataclass
from uuid import uuid4

from app.domain.work_plans import WorkPlan

from .dto import CreateWorkPlanCommand, WorkPlanActor
from .ports import WorkPlanRepository


@dataclass(slots=True)
class CreateWorkPlanUseCase:
    repository: WorkPlanRepository

    def execute(self, command: CreateWorkPlanCommand, actor: WorkPlanActor) -> WorkPlan:
        if actor.role not in {"admin", "manager"}:
            from app.domain.work_plans import WorkPlanForbiddenError

            raise WorkPlanForbiddenError("Forbidden")
        return self.repository.create_work_plan(
            WorkPlan(
                work_plan_id=uuid4(),
                user_id=command.user_id,
                date=command.date,
                summ=command.summ,
                description=command.description,
            )
        )
