from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.database.time_utils import utc_epoch_seconds
from app.domain.works import Work

from .dto import CreateWorkCommand
from .ports import WorkRepository


@dataclass(slots=True)
class CreateWorkUseCase:
    repository: WorkRepository

    def execute(self, command: CreateWorkCommand) -> Work:
        work = Work(
            work_id=uuid4(),
            name=command.name,
            category={"work_category_id": str(command.category)} if command.category else None,
            measurement_unit=command.measurement_unit,
            created_at=utc_epoch_seconds(),
            created_by=command.created_by,
            deleted=False,
            work_prices=[],
        )
        return self.repository.create_work(work)
