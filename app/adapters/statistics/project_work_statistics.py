"""Redis-backed statistics grouped by project and work."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from app.database.managers.projects_managers import ProjectsManager
from app.use_cases.projects.dto import ProjectStatsMap

from .redis_client import RedisClient

KEY_PREFIX = "project-work-stats"


class ProjectStatsSource(Protocol):
    def get_project_stats(self, project_id: UUID) -> ProjectStatsMap: ...

    def get_all_project_ids(self) -> list[UUID]: ...


class ProjectWorkStatistics(Protocol):
    def get_project_stats(self, project_id: UUID) -> ProjectStatsMap: ...

    def recalculate_many(self, project_ids: set[UUID]) -> None: ...


def _key(project_id: UUID) -> str:
    return f"{KEY_PREFIX}:{project_id}"


@dataclass(slots=True)
class RedisProjectWorkStatistics:
    """Reads cached maps and atomically replaces one project's map on refresh."""

    client: RedisClient
    projects_manager: ProjectStatsSource = field(default_factory=ProjectsManager)

    def get_project_stats(self, project_id: UUID) -> ProjectStatsMap:
        raw = self.client.get(_key(project_id))
        if raw is None:
            return {}
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            raise ValueError("Invalid project-work statistics cache payload")
        return loaded

    def recalculate(self, project_id: UUID) -> ProjectStatsMap:
        stats = self.projects_manager.get_project_stats(project_id)
        key = _key(project_id)
        if stats:
            self.client.set(key, json.dumps(stats, ensure_ascii=False))
        else:
            self.client.delete(key)
        return stats

    def recalculate_many(self, project_ids: set[UUID]) -> None:
        for project_id in project_ids:
            self.recalculate(project_id)

    def recalculate_all(self) -> int:
        project_ids = self.projects_manager.get_all_project_ids()
        self.recalculate_many(set(project_ids))
        return len(project_ids)
