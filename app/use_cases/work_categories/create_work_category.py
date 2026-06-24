from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.database.time_utils import utc_epoch_seconds
from app.domain.work_categories import WorkCategory

from .dto import CreateWorkCategoryCommand
from .ports import WorkCategoryRepository


@dataclass(slots=True)
class CreateWorkCategoryUseCase:
    repository: WorkCategoryRepository

    def execute(self, command: CreateWorkCategoryCommand) -> WorkCategory:
        work_category = WorkCategory(
            work_category_id=uuid4(),
            name=command.name,
            created_by=command.created_by,
            created_at=utc_epoch_seconds(),
            deleted=False,
        )
        return self.repository.create_work_category(work_category)
