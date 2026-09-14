from __future__ import annotations

from dataclasses import dataclass

from app.domain.project_works import (
    ProjectWork,
    ProjectWorkForbiddenError,
    ProjectWorkNotFoundError,
)

from .create_project_work import _calculate_summ, _owned_project_ids
from .dto import ProjectWorkActor, UpdateProjectWorkCommand
from .ports import ProjectWorkRepository


@dataclass(slots=True)
class UpdateProjectWorkUseCase:
    repository: ProjectWorkRepository

    def execute(
        self, command: UpdateProjectWorkCommand, actor: ProjectWorkActor
    ) -> ProjectWork:
        current = self.repository.get_project_work(command.project_work_id)
        if current is None:
            raise ProjectWorkNotFoundError("Project work not found")

        if actor.role == "project-leader":
            owned_project_ids = _owned_project_ids(self.repository, actor)
            target_project = command.project if command.project is not None else current.project
            if target_project not in owned_project_ids:
                raise ProjectWorkForbiddenError("Forbidden")
            if current.signed is True:
                raise ProjectWorkForbiddenError("User cannot edit signed shift report")

        changes: dict[str, object] = {}
        if command.project is not None:
            changes["project"] = command.project
        if command.project_work_name is not None:
            changes["project_work_name"] = command.project_work_name
        if command.work is not None:
            changes["work"] = command.work
        if command.quantity is not None:
            changes["quantity"] = command.quantity
        if command.price is not None:
            changes["price"] = command.price
        if command.signed is not None:
            changes["signed"] = command.signed

        if command.price is not None or command.quantity is not None:
            price = command.price if command.price is not None else current.price
            quantity = command.quantity if command.quantity is not None else current.quantity
            changes["summ"] = _calculate_summ(price, quantity)

        if not changes:
            return current

        updated = self.repository.update_project_work(current.with_updates(**changes))
        if updated is None:
            raise ProjectWorkNotFoundError("Project work not found")
        return updated
