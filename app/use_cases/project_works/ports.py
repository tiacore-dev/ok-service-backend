from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.project_works import ProjectWork

from .dto import ProjectWorkListQuery


class ProjectWorkRepository(Protocol):
    def create_project_work(self, project_work: ProjectWork) -> ProjectWork: ...

    def create_project_works(
        self, project_works: list[ProjectWork]
    ) -> list[ProjectWork]: ...

    def get_project_work(self, project_work_id: UUID) -> ProjectWork | None: ...

    def update_project_work(self, project_work: ProjectWork) -> ProjectWork | None: ...

    def delete_project_work(self, project_work_id: UUID) -> bool: ...

    def list_project_works(self, query: ProjectWorkListQuery) -> list[ProjectWork]: ...

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]: ...
