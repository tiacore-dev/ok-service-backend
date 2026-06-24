from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.adapters._typing import normalize_result
from app.database.managers.works_managers import WorkCategoriesManager
from app.domain.work_categories import WorkCategory
from app.use_cases.work_categories.dto import WorkCategoryListQuery
from app.use_cases.work_categories.ports import WorkCategoryRepository

from .mappers import work_category_dict_to_entity


@dataclass(slots=True)
class SQLAlchemyWorkCategoryRepository(WorkCategoryRepository):
    manager: WorkCategoriesManager = field(default_factory=WorkCategoriesManager)

    def create_work_category(self, work_category: WorkCategory) -> WorkCategory:
        created = self.manager.add(
            created_by=work_category.created_by,
            name=work_category.name,
        )
        record = normalize_result(created)
        if record is None:
            raise ValueError("Work category creation did not return a record")
        return work_category_dict_to_entity(record)

    def get_work_category(self, work_category_id: UUID) -> WorkCategory | None:
        record = normalize_result(self.manager.get_by_id(work_category_id))
        if record is None:
            return None
        return work_category_dict_to_entity(record)

    def update_work_category(self, work_category: WorkCategory) -> WorkCategory | None:
        updated = self.manager.update(
            record_id=work_category.work_category_id,
            name=work_category.name,
            deleted=work_category.deleted,
        )
        record = normalize_result(updated)
        if record is None:
            return None
        return work_category_dict_to_entity(record)

    def delete_work_category(self, work_category_id: UUID) -> bool:
        deleted = self.manager.delete(work_category_id)
        return deleted is not None

    def list_work_categories(self, query: WorkCategoryListQuery) -> list[WorkCategory]:
        records = self.manager.get_all_filtered(
            offset=query.offset,
            limit=query.limit,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            name=query.name,
            deleted=query.deleted,
        )
        return [work_category_dict_to_entity(record) for record in records]
