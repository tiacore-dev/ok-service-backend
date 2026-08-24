from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.adapters.project_works.sqlalchemy_repository import (
    SQLAlchemyProjectWorkRepository,
)
from app.domain.project_works import ProjectWork
from app.use_cases.projects.dto import ProjectStatsMap
from app.web.project_works.routes import _response_with_stats


class FakeManager:
    def __init__(self, record: dict[str, Any]):
        self.record = record

    def add(self, **_kwargs: object) -> dict[str, Any]:
        return self.record

    def get_by_id(self, record_id: UUID) -> dict[str, Any]:
        return self.record

    def update(self, record_id: UUID, **_kwargs: object) -> dict[str, Any]:
        return self.record

    def delete(self, record_id: UUID) -> dict[str, Any]:
        return self.record

    def get_all_filtered(
        self,
        offset: int = 0,
        limit: int | None = None,
        sort_by: str | None = "created_at",
        sort_order: str = "desc",
        **filters: Any,
    ) -> list[dict[str, Any]]:
        return [self.record]


class FakeStatistics:
    def __init__(self):
        self.recalculated: list[set[UUID]] = []

    def recalculate_many(self, project_ids: set[UUID]) -> None:
        self.recalculated.append(project_ids)

    def get_project_stats(self, project_id: UUID) -> ProjectStatsMap:
        return {}

    def delete_project_stats(self, project_id: UUID) -> None:
        return None


def _project_work():
    return ProjectWork(
        project_work_id=uuid4(),
        project_work_name="Монтаж",
        project=uuid4(),
        work=uuid4(),
        quantity=Decimal("10"),
        summ=None,
        created_by=uuid4(),
        created_at=1,
        signed=False,
    )


def _record(item):
    return {
        "project_work_id": str(item.project_work_id),
        "project_work_name": item.project_work_name,
        "project": str(item.project),
        "work": str(item.work),
        "quantity": item.quantity,
        "summ": item.summ,
        "created_by": str(item.created_by),
        "created_at": item.created_at,
        "signed": item.signed,
    }


def test_project_work_mutations_recalculate_affected_project():
    item = _project_work()
    statistics = FakeStatistics()
    repository = SQLAlchemyProjectWorkRepository(
        manager=FakeManager(_record(item)), statistics=statistics
    )

    repository.create_project_work(item)
    repository.update_project_work(item)
    repository.delete_project_work(item.project_work_id)

    assert statistics.recalculated == [{item.project}, {item.project}, {item.project}]


def test_project_work_response_uses_cached_stat_and_acceptance_status():
    item = _project_work()

    response = _response_with_stats(
        item,
        {
            str(item.work): {
                "project_work_quantity": 10.0,
                "shift_report_details_quantity": 5.0,
            }
        },
    )

    assert response["project_work_quantity"] == 10.0
    assert response["shift_report_details_quantity"] == 5.0
    assert response["acceptance_status"] == "partial"
