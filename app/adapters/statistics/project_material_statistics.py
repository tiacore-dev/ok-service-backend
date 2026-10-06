"""Redis-backed statistics grouped by project and material."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from redis.exceptions import RedisError

from app.database.managers.projects_managers import ProjectsManager
from app.use_cases.projects.dto import ProjectStatsMap

from .redis_client import RedisClient

KEY_PREFIX = "project-material-stats"
REQUIRED_STAT_FIELDS = {
    "project_material_quantity",
    "project_material_summ",
    "shift_report_material_quantity",
    "shift_report_material_summ_by_estimate",
}
logger = logging.getLogger("ok_service")


class ProjectMaterialStatsSource(Protocol):
    def get_project_material_stats(self, project_id: UUID) -> ProjectStatsMap: ...

    def get_all_project_ids(self) -> list[UUID]: ...


class ProjectMaterialStatistics(Protocol):
    def get_project_material_stats(self, project_id: UUID) -> ProjectStatsMap: ...

    def recalculate_many(self, project_ids: set[UUID]) -> None: ...

    def delete_project_stats(self, project_id: UUID) -> None: ...


def _key(project_id: UUID) -> str:
    return f"{KEY_PREFIX}:{project_id}"


@dataclass(slots=True)
class RedisProjectMaterialStatistics:
    client: RedisClient
    projects_manager: ProjectMaterialStatsSource = field(default_factory=ProjectsManager)

    def get_project_material_stats(self, project_id: UUID) -> ProjectStatsMap:
        try:
            raw = self.client.get(_key(project_id))
            if raw is not None:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                loaded = json.loads(raw)
                if isinstance(loaded, dict) and loaded and all(
                    isinstance(value, dict)
                    and REQUIRED_STAT_FIELDS <= value.keys()
                    for value in loaded.values()
                ):
                    return loaded
                logger.info("Refreshing outdated project-material statistics cache payload")
        except (RedisError, UnicodeDecodeError, json.JSONDecodeError) as error:
            logger.warning("Redis material statistics read failed: %s", error)
        return self.recalculate(project_id)

    def recalculate(self, project_id: UUID) -> ProjectStatsMap:
        stats = self.projects_manager.get_project_material_stats(project_id)
        key = _key(project_id)
        if stats:
            try:
                self.client.set(key, json.dumps(stats, ensure_ascii=False))
            except RedisError as error:
                logger.warning("Redis material statistics write failed: %s", error)
        else:
            self.delete_project_stats(project_id)
        return stats

    def delete_project_stats(self, project_id: UUID) -> None:
        try:
            self.client.delete(_key(project_id))
        except RedisError as error:
            logger.warning("Redis material statistics delete failed: %s", error)

    def recalculate_many(self, project_ids: set[UUID]) -> None:
        for project_id in project_ids:
            self.recalculate(project_id)

    def recalculate_all(self) -> int:
        project_ids = self.projects_manager.get_all_project_ids()
        self.recalculate_many(set(project_ids))
        return len(project_ids)
