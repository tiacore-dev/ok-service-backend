from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.works import Work, WorkNotFoundError

from .ports import WorkRepository


@dataclass(slots=True)
class GetWorkUseCase:
    repository: WorkRepository

    def execute(self, work_id: UUID) -> Work:
        work = self.repository.get_work(work_id)
        if work is None:
            raise WorkNotFoundError("Work not found")
        return work
