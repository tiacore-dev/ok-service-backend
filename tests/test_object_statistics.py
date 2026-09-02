from uuid import UUID, uuid4

import pytest

from app.domain.objects import Object, ObjectForbiddenError, ObjectNotFoundError
from app.use_cases.objects import ObjectListQuery
from app.use_cases.objects import (
    GetObjectStatsDetailsUseCase,
    GetObjectStatsUseCase,
    ObjectActor,
)


def test_project_stats_summary_preserves_null_acceptance_values():
    from app.database.managers.projects_managers import ProjectsManager

    stats = {
        "work-1": {
            "project_work_quantity": 10.0,
            "project_work_summ": 100.0,
            "shift_report_details_quantity": 4.0,
            "shift_report_details_summ": 40.0,
            "shift_report_details_summ_by_estimate": 40.0,
            "presented_quantity": None,
            "presented_summ": None,
            "accepted_quantity": None,
            "accepted_summ": None,
        }
    }

    assert ProjectsManager._summarize_project_stats(stats) == {
        "project_work_quantity": 10.0,
        "project_work_summ": 100.0,
        "shift_report_details_quantity": 4.0,
        "shift_report_details_summ": 40.0,
        "shift_report_details_summ_by_estimate": 40.0,
        "presented_quantity": None,
        "presented_summ": None,
        "accepted_quantity": None,
        "accepted_summ": None,
    }


class FakeObjectRepository:
    def __init__(self, stats: dict[str, object] | None = None, exists: bool = True):
        self.stats: dict[str, object] = stats or {"total": {}, "projects": []}
        self.obj: Object | None = (
            Object(
                object_id=uuid4(),
                name="Object",
                address=None,
                description=None,
                city_id=None,
                status="active",
                manager=None,
                lng=None,
                ltd=None,
                created_by=None,
                created_at=1,
            )
            if exists
            else None
        )

    def create_object(self, obj: Object) -> Object:
        self.obj = obj
        return obj

    def get_object(self, object_id: UUID) -> Object | None:
        return self.obj if self.obj is not None else None

    def update_object(self, obj: Object) -> Object | None:
        self.obj = obj
        return obj

    def delete_object(self, object_id: UUID) -> bool:
        return self.obj is not None and self.obj.object_id == object_id

    def list_objects(self, query: ObjectListQuery, actor: ObjectActor) -> list[Object]:
        return [self.obj] if self.obj is not None else []

    def update_object_with_projects_closed(self, obj: Object) -> Object | None:
        return self.update_object(obj)

    def get_object_stats(self, object_id: UUID) -> dict[str, object]:
        return self.stats

    def get_object_stats_details(self, object_id: UUID) -> dict[str, object]:
        return self.stats


def test_object_stats_use_case_returns_total_and_projects():
    stats = {"total": {"accepted_summ": 120.0}, "projects": []}
    result = GetObjectStatsUseCase(FakeObjectRepository(stats)).execute(
        uuid4(), ObjectActor("manager", uuid4())
    )

    assert result == stats


def test_object_stats_details_use_case_returns_work_grouped_stats():
    stats = {
        "total": {"work-id": {"accepted_quantity": 5.0}},
        "projects": [],
    }
    result = GetObjectStatsDetailsUseCase(FakeObjectRepository(stats)).execute(
        uuid4(), ObjectActor("manager", uuid4())
    )

    assert result == stats


def test_object_stats_use_case_rejects_user():
    with pytest.raises(ObjectForbiddenError):
        GetObjectStatsUseCase(FakeObjectRepository()).execute(
            uuid4(), ObjectActor("user", uuid4())
        )


def test_object_stats_use_case_rejects_unknown_object():
    with pytest.raises(ObjectNotFoundError):
        GetObjectStatsUseCase(FakeObjectRepository(exists=False)).execute(
            uuid4(), ObjectActor("manager", uuid4())
        )
