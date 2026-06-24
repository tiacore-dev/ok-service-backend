from __future__ import annotations

from dataclasses import dataclass

from .dto import WorkCategoryListQuery
from .ports import WorkCategoryRepository


@dataclass(slots=True)
class ListWorkCategoriesUseCase:
    repository: WorkCategoryRepository

    def execute(self, query: WorkCategoryListQuery):
        return self.repository.list_work_categories(query)
