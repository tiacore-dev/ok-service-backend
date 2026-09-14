from dataclasses import dataclass

from app.domain.work_plans import WorkPlan, WorkPlanForbiddenError, WorkPlanNotFoundError

from .dto import UpdateWorkPlanCommand, WorkPlanActor
from .ports import WorkPlanRepository


@dataclass(slots=True)
class UpdateWorkPlanUseCase:
    repository: WorkPlanRepository

    def execute(self, command: UpdateWorkPlanCommand, actor: WorkPlanActor) -> WorkPlan:
        if actor.role not in {"admin", "manager"}:
            raise WorkPlanForbiddenError("Forbidden")
        current = self.repository.get_work_plan(command.work_plan_id)
        if current is None:
            raise WorkPlanNotFoundError("Work plan not found")
        changes = {}
        if command.user_id_is_set:
            changes["user_id"] = command.user_id
        if command.date_is_set:
            changes["date"] = command.date
        if command.summ_is_set:
            changes["summ"] = command.summ
        if command.description_is_set:
            changes["description"] = command.description
        if not changes:
            return current
        result = self.repository.update_work_plan(current.with_updates(**changes))
        if result is None:
            raise WorkPlanNotFoundError("Work plan not found")
        return result
