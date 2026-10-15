"""Infrastructure adapters used by project-work statistics."""

from .project_work_statistics import ProjectWorkStatistics, RedisProjectWorkStatistics
from .project_material_statistics import (
    ProjectMaterialStatistics,
    RedisProjectMaterialStatistics,
)
from .redis_client import create_redis_client
from .material_statistics_helpers import (
    MATERIAL_SUMMARY_FIELDS,
    merge_material_stats,
    summarize_material_stats,
)

__all__ = [
    "create_redis_client",
    "ProjectWorkStatistics",
    "RedisProjectWorkStatistics",
    "ProjectMaterialStatistics",
    "RedisProjectMaterialStatistics",
    "MATERIAL_SUMMARY_FIELDS",
    "merge_material_stats",
    "summarize_material_stats",
]
