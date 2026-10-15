from uuid import UUID, uuid4

import pytest

from app.adapters.statistics.project_material_statistics import (
    RedisProjectMaterialStatistics,
)
from app.use_cases.projects.dto import ProjectStatsMap


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.deleted: list[str] = []

    def get(self, name: str) -> str | None:
        return self.values.get(name)

    def set(self, name: str, value: str) -> bool:
        self.values[name] = value
        return True

    def delete(self, *names: str) -> int:
        self.deleted.extend(names)
        for name in names:
            self.values.pop(name, None)
        return len(names)


class FakeProjectsManager:
    def __init__(self, stats: ProjectStatsMap):
        self.stats = stats

    def get_project_material_stats(self, project_id: UUID) -> ProjectStatsMap:
        return self.stats

    def get_all_project_ids(self) -> list[UUID]:
        return []


class FailingProjectsManager:
    def get_project_material_stats(self, project_id: UUID) -> ProjectStatsMap:
        raise RuntimeError("database is unavailable")

    def get_all_project_ids(self) -> list[UUID]:
        return []


def test_material_statistics_cache_uses_a_separate_key_and_preserves_all_fields():
    project_id = uuid4()
    expected = {
        str(uuid4()): {
            "project_material_quantity": 12.0,
            "project_material_summ": 1200.0,
            "shift_report_material_quantity": 5.0,
            "shift_report_material_summ_by_estimate": 500.0,
            "material_name": "Concrete",
        }
    }
    redis = FakeRedis()
    service = RedisProjectMaterialStatistics(redis, FakeProjectsManager(expected))

    assert service.recalculate(project_id) == expected
    assert service.get_project_material_stats(project_id) == expected
    assert f"project-material-stats:{project_id}" in redis.values


def test_material_statistics_cache_refreshes_an_outdated_payload():
    project_id = uuid4()
    redis = FakeRedis()
    redis.values[f"project-material-stats:{project_id}"] = "{}"
    expected = {
        "material": {
            "project_material_quantity": 1.0,
            "project_material_summ": 2.0,
            "shift_report_material_quantity": 3.0,
            "shift_report_material_summ_by_estimate": 6.0,
        }
    }

    assert RedisProjectMaterialStatistics(
        redis, FakeProjectsManager(expected)
    ).get_project_material_stats(project_id) == expected


def test_database_error_does_not_delete_existing_material_statistics_cache():
    project_id = uuid4()
    key = f"project-material-stats:{project_id}"
    redis = FakeRedis()
    redis.values[key] = '{"material": {"project_material_quantity": 1.0}}'
    service = RedisProjectMaterialStatistics(redis, FailingProjectsManager())

    with pytest.raises(RuntimeError, match="database is unavailable"):
        service.recalculate(project_id)

    assert redis.values[key] == '{"material": {"project_material_quantity": 1.0}}'
    assert redis.deleted == []
