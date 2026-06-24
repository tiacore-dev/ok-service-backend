from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.works import Work

from .dto import CreateWorkCommand, UpdateWorkCommand, WorkListQuery


class WorkRepository(Protocol):
    def create_work(self, work: Work) -> Work: ...

    def get_work(self, work_id: UUID) -> Work | None: ...

    def update_work(self, work: Work) -> Work | None: ...

    def delete_work(self, work_id: UUID) -> bool: ...

    def list_works(self, query: WorkListQuery) -> list[Work]: ...
