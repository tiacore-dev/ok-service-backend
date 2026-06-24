from __future__ import annotations

from dataclasses import dataclass

from app.domain.work_categories import WorkCategoryNotFoundError

from .dto import UpdateWorkCategoryCommand
from .ports import WorkCategoryRepository


@dataclass(slots=True)
class UpdateWorkCategoryUseCase:
    repository: WorkCategoryRepository

    def execute(self, command: UpdateWorkCategoryCommand):
        existing = self.repository.get_work_category(command.work_category_id)
        if existing is None:
            raise WorkCategoryNotFoundError("Work category not found")

        changes = {}
        if command.name is not None:
            changes["name"] = command.name
        if command.deleted is not None:
            changes["deleted"] = command.deleted
        if not changes:
            return existing

        result = self.repository.update_work_category(existing.with_updates(**changes))
        if result is None:
            raise WorkCategoryNotFoundError("Work category not found")
        return result
