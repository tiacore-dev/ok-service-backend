from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .ports import WorkCategoryRepository


@dataclass(slots=True)
class DeleteWorkCategoryUseCase:
    repository: WorkCategoryRepository

    def execute(self, work_category_id: UUID) -> bool:
        return self.repository.delete_work_category(work_category_id)
