from uuid import UUID, uuid4

from app.adapters.statistics.project_work_statistics import (
    RedisProjectWorkStatistics,
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

    def get_project_stats(self, project_id: UUID) -> ProjectStatsMap:
        return self.stats

    def get_all_project_ids(self) -> list[UUID]:
        return []


def test_recalculate_replaces_one_project_stats_without_ttl():
    project_id = uuid4()
    client = FakeRedis()
    expected = {
        str(uuid4()): {
            "project_work_quantity": 12.0,
            "shift_report_details_quantity": 5.0,
            "project_work_name": "Монтаж",
        }
    }
    service = RedisProjectWorkStatistics(client, FakeProjectsManager(expected))

    assert service.recalculate(project_id) == expected
    assert service.get_project_stats(project_id) == expected


def test_recalculate_removes_empty_project_stats():
    project_id = uuid4()
    client = FakeRedis()
    service = RedisProjectWorkStatistics(client, FakeProjectsManager({}))

    service.recalculate(project_id)

    assert service.get_project_stats(project_id) == {}
    assert client.deleted == [f"project-work-stats:{project_id}"]
