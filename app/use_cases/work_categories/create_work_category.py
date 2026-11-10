from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.domain.work_categories import WorkCategory

from .dto import CreateWorkCategoryCommand
from .hierarchy import ensure_valid_parent
from .ports import WorkCategoryRepository
from ..time_utils import utc_epoch_milliseconds


@dataclass(slots=True)
class CreateWorkCategoryUseCase:
    repository: WorkCategoryRepository

    def execute(self, command: CreateWorkCategoryCommand) -> WorkCategory:
        work_category_id = uuid4()
        if command.parent_id is not None:
            ensure_valid_parent(self.repository, work_category_id, command.parent_id)
        work_category = WorkCategory(
            work_category_id=work_category_id,
            name=command.name,
            created_by=command.created_by,
            created_at=utc_epoch_milliseconds(),
            deleted=False,
            parent_id=command.parent_id,
        )
        return self.repository.create_work_category(work_category)
