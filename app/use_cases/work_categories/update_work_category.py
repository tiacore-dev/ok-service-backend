from __future__ import annotations

from dataclasses import dataclass

from app.domain.work_categories import WorkCategoryNotFoundError

from .dto import UpdateWorkCategoryCommand
from .hierarchy import ensure_valid_parent
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
        if command.parent_id_is_set and command.parent_id != existing.parent_id:
            if command.parent_id is not None:
                ensure_valid_parent(
                    self.repository, existing.work_category_id, command.parent_id
                )
            changes["parent_id"] = command.parent_id
        if not changes:
            return existing

        result = self.repository.update_work_category(existing.with_updates(**changes))
        if result is None:
            raise WorkCategoryNotFoundError("Work category not found")
        return result
