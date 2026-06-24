from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.work_categories import WorkCategory

from .dto import WorkCategoryListQuery


class WorkCategoryRepository(Protocol):
    def create_work_category(self, work_category: WorkCategory) -> WorkCategory: ...

    def get_work_category(self, work_category_id: UUID) -> WorkCategory | None: ...

    def update_work_category(self, work_category: WorkCategory) -> WorkCategory | None: ...

    def delete_work_category(self, work_category_id: UUID) -> bool: ...

    def list_work_categories(self, query: WorkCategoryListQuery) -> list[WorkCategory]: ...
