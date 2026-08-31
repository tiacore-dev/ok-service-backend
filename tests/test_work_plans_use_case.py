from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain.work_plans import WorkPlan, WorkPlanForbiddenError, WorkPlanValidationError
from app.use_cases.work_plans import (
    CreateWorkPlanCommand, CreateWorkPlanUseCase, SoftDeleteWorkPlanUseCase,
    UpdateWorkPlanCommand, UpdateWorkPlanUseCase, WorkPlanActor, WorkPlanListQuery,
)


class FakeRepository:
    def __init__(self, item: WorkPlan | None = None):
        self.item: WorkPlan | None = item
        self.deleted: UUID | None = None

    def create_work_plan(self, work_plan: WorkPlan) -> WorkPlan:
        self.item = work_plan
        return work_plan

    def get_work_plan(self, work_plan_id: UUID) -> WorkPlan | None:
        return self.item if self.item and self.item.work_plan_id == work_plan_id else None

    def update_work_plan(self, work_plan: WorkPlan) -> WorkPlan:
        self.item = work_plan
        return work_plan

    def delete_work_plan(self, work_plan_id: UUID) -> bool:
        self.deleted = work_plan_id
        return True

    def list_work_plans(self, query: WorkPlanListQuery) -> list[WorkPlan]:
        return [self.item] if self.item is not None else []


def test_work_plan_rejects_non_first_day_and_negative_summ():
    with pytest.raises(WorkPlanValidationError):
        WorkPlan(uuid4(), None, date(2026, 8, 2), Decimal("0"), None)
    with pytest.raises(WorkPlanValidationError):
        WorkPlan(uuid4(), None, date(2026, 8, 1), Decimal("-1"), None)
    with pytest.raises(WorkPlanValidationError):
        WorkPlan(uuid4(), None, date(2026, 8, 1), Decimal("1.999"), None)
    with pytest.raises(WorkPlanValidationError):
        WorkPlan(uuid4(), None, date(2026, 8, 1), Decimal("10000000000.00"), None)


def test_manager_can_create_company_plan_with_zero_summ():
    repository = FakeRepository()
    item = CreateWorkPlanUseCase(repository).execute(
        CreateWorkPlanCommand(None, date(2026, 8, 1), Decimal("0"), None),
        WorkPlanActor("manager"),
    )
    assert item.user_id is None
    assert item.summ == Decimal("0")


def test_only_admin_and_manager_can_mutate_and_nullable_fields_are_clearable():
    repository = FakeRepository(WorkPlan(uuid4(), uuid4(), date(2026, 8, 1), Decimal("10"), "text"))
    assert repository.item is not None
    work_plan_id = repository.item.work_plan_id
    with pytest.raises(WorkPlanForbiddenError):
        UpdateWorkPlanUseCase(repository).execute(UpdateWorkPlanCommand(work_plan_id), WorkPlanActor("user"))
    updated = UpdateWorkPlanUseCase(repository).execute(
        UpdateWorkPlanCommand(work_plan_id, user_id=None, user_id_is_set=True, description=None, description_is_set=True),
        WorkPlanActor("admin"),
    )
    assert updated.user_id is None
    assert updated.description is None


def test_soft_delete_sets_deleted_flag():
    item = WorkPlan(uuid4(), None, date(2026, 8, 1), Decimal("10"), None)
    result = SoftDeleteWorkPlanUseCase(FakeRepository(item)).execute(item.work_plan_id, WorkPlanActor("manager"))
    assert result.deleted is True


def test_work_plan_response_preserves_fixed_decimal_scale():
    from app.adapters.work_plans import work_plan_entity_to_response

    item = WorkPlan(uuid4(), None, date(2026, 8, 1), Decimal("1.2"), None)
    assert work_plan_entity_to_response(item)["summ"] == "1.20"


@pytest.mark.parametrize("role", ["admin", "manager"])
def test_manager_and_admin_can_update_work_plan(role: str):
    item = WorkPlan(uuid4(), None, date(2026, 8, 1), Decimal("10"), None)
    repository = FakeRepository(item)

    updated = UpdateWorkPlanUseCase(repository).execute(
        UpdateWorkPlanCommand(item.work_plan_id, summ=Decimal("20"), summ_is_set=True),
        WorkPlanActor(role),
    )

    assert updated.summ == Decimal("20")
