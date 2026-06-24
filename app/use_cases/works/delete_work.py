from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.works import WorkNotFoundError

from .ports import WorkRepository


@dataclass(slots=True)
class SoftDeleteWorkUseCase:
    repository: WorkRepository

    def execute(self, work_id: UUID) -> bool:
        current = self.repository.get_work(work_id)
        if current is None:
            raise WorkNotFoundError("Work not found")
        updated = self.repository.update_work(current.with_updates(deleted=True))
        if updated is None:
            raise WorkNotFoundError("Work not found")
        return True


@dataclass(slots=True)
class HardDeleteWorkUseCase:
    repository: WorkRepository

    def execute(self, work_id: UUID) -> bool:
        current = self.repository.get_work(work_id)
        if current is None:
            raise WorkNotFoundError("Work not found")
        deleted = self.repository.delete_work(work_id)
        if not deleted:
            raise WorkNotFoundError("Work not found")
        return deleted
