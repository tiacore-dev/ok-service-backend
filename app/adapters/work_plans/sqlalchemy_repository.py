from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.work_plans_manager import WorkPlansManager
from app.domain.work_plans import WorkPlan
from app.use_cases.work_plans.dto import WorkPlanListQuery
from app.use_cases.work_plans.ports import WorkPlanRepository

from .mappers import work_plan_dict_to_entity


@dataclass(slots=True)
class SQLAlchemyWorkPlanRepository(WorkPlanRepository):
    manager: WorkPlansManager = field(default_factory=WorkPlansManager)

    def create_work_plan(self, work_plan: WorkPlan) -> WorkPlan:
        record = normalize_result(self.manager.add(**{
            "work_plan_id": work_plan.work_plan_id,
            "user_id": work_plan.user_id,
            "date": work_plan.date,
            "summ": work_plan.summ,
            "description": work_plan.description,
            "deleted": work_plan.deleted,
        }))
        if record is None:
            raise ValueError("Work plan creation did not return a record")
        return work_plan_dict_to_entity(record)

    def get_work_plan(self, work_plan_id: UUID) -> WorkPlan | None:
        record = normalize_result(self.manager.get_by_id(work_plan_id))
        return work_plan_dict_to_entity(record) if record is not None else None

    def update_work_plan(self, work_plan: WorkPlan) -> WorkPlan | None:
        record = normalize_result(self.manager.update(
            record_id=work_plan.work_plan_id,
            user_id=work_plan.user_id,
            date=work_plan.date,
            summ=work_plan.summ,
            description=work_plan.description,
            deleted=work_plan.deleted,
        ))
        return work_plan_dict_to_entity(record) if record is not None else None

    def delete_work_plan(self, work_plan_id: UUID) -> bool:
        return self.manager.delete(work_plan_id) is not None

    def list_work_plans(self, query: WorkPlanListQuery) -> list[WorkPlan]:
        records = self.manager.get_all_filtered(
            offset=query.offset, limit=query.limit, sort_by=query.sort_by,
            sort_order=query.sort_order, year=query.year, user_id=query.user_id,
            user_id_is_null=query.user_id_is_null, deleted=query.deleted,
        )
        return [work_plan_dict_to_entity(record) for record in records]
