from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.work_categories import WorkCategoryNotFoundError

from .ports import WorkCategoryRepository


@dataclass(slots=True)
class GetWorkCategoryUseCase:
    repository: WorkCategoryRepository

    def execute(self, work_category_id: UUID):
        work_category = self.repository.get_work_category(work_category_id)
        if work_category is None:
            raise WorkCategoryNotFoundError("Work category not found")
        return work_category
