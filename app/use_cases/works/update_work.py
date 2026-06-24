from __future__ import annotations

from dataclasses import dataclass

from app.domain.works import Work, WorkNotFoundError

from .dto import UpdateWorkCommand
from .ports import WorkRepository


@dataclass(slots=True)
class UpdateWorkUseCase:
    repository: WorkRepository

    def execute(self, command: UpdateWorkCommand) -> Work:
        current = self.repository.get_work(command.work_id)
        if current is None:
            raise WorkNotFoundError("Work not found")

        changes: dict[str, object] = {}
        if command.name is not None:
            changes["name"] = command.name
        if command.category is not None:
            changes["category"] = {"work_category_id": str(command.category)}
        if command.measurement_unit is not None:
            changes["measurement_unit"] = command.measurement_unit
        if command.deleted is not None:
            changes["deleted"] = command.deleted

        if not changes:
            return current

        updated = self.repository.update_work(current.with_updates(**changes))
        if updated is None:
            raise WorkNotFoundError("Work not found")
        return updated
