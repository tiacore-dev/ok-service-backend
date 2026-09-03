from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.projects import ProjectForbiddenError, ProjectNotFoundError

from .dto import ProjectActor, ProjectLeaderStatsListQuery
from .ports import ProjectRepository


@dataclass(slots=True)
class GetProjectUseCase:
    repository: ProjectRepository

    def execute(self, project_id: UUID, actor: ProjectActor) -> dict[str, object]:
        record = self.repository.get_project_record(project_id)
        if record is None:
            raise ProjectNotFoundError("Project not found")
        return record


@dataclass(slots=True)
class GetProjectStatsUseCase:
    repository: ProjectRepository

    def execute(self, project_id: UUID, actor: ProjectActor):
        if actor.role == "user":
            raise ProjectForbiddenError("Forbidden")
        return self.repository.get_project_stats(project_id)


@dataclass(slots=True)
class GetProjectStatsByMaterialsUseCase:
    repository: ProjectRepository

    def execute(self, project_id: UUID, actor: ProjectActor):
        if actor.role == "user":
            raise ProjectForbiddenError("Forbidden")
        return self.repository.get_project_stats_by_materials(project_id)


@dataclass(slots=True)
class GetProjectLeaderStatsUseCase:
    repository: ProjectRepository

    def execute(self, project_leader_id: UUID, actor: ProjectActor) -> dict[str, object]:
        if actor.role == "project-leader" and actor.user_id != project_leader_id:
            raise ProjectForbiddenError("Forbidden")
        if actor.role not in {"admin", "manager", "project-leader"}:
            raise ProjectForbiddenError("Forbidden")
        return self.repository.get_project_leader_stats(project_leader_id)


@dataclass(slots=True)
class GetProjectLeaderStatsDetailsUseCase:
    repository: ProjectRepository

    def execute(self, project_leader_id: UUID, actor: ProjectActor) -> dict[str, object]:
        if actor.role == "project-leader" and actor.user_id != project_leader_id:
            raise ProjectForbiddenError("Forbidden")
        if actor.role not in {"admin", "manager", "project-leader"}:
            raise ProjectForbiddenError("Forbidden")
        return self.repository.get_project_leader_stats_details(project_leader_id)


@dataclass(slots=True)
class GetAllProjectLeadersStatsUseCase:
    repository: ProjectRepository

    def execute(
        self, query: ProjectLeaderStatsListQuery, actor: ProjectActor
    ) -> dict[str, object]:
        if actor.role not in {"admin", "manager"}:
            raise ProjectForbiddenError("Forbidden")
        return self.repository.get_all_project_leaders_stats(query)
