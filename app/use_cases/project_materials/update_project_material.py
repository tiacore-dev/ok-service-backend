from __future__ import annotations

from dataclasses import dataclass

from app.domain.project_materials import (
    ProjectMaterial,
    ProjectMaterialForbiddenError,
    ProjectMaterialNotFoundError,
)

from .create_project_material import _calculate_summ
from .dto import ProjectMaterialActor, UpdateProjectMaterialCommand
from .ports import ProjectMaterialRepository


@dataclass(slots=True)
class UpdateProjectMaterialUseCase:
    repository: ProjectMaterialRepository

    def execute(
        self, command: UpdateProjectMaterialCommand, actor: ProjectMaterialActor
    ) -> ProjectMaterial:
        current = self.repository.get_project_material(command.project_material_id)
        if current is None:
            raise ProjectMaterialNotFoundError("Project material not found")
        if actor.role not in {"admin", "manager"}:
            if actor.role != "project-leader":
                raise ProjectMaterialForbiddenError("Forbidden")
            owned_projects = set(
                self.repository.get_project_ids_by_leader(actor.user_id)
            )
            if current.project not in owned_projects or (
                command.project_is_set and command.project not in owned_projects
            ):
                raise ProjectMaterialForbiddenError(
                    "You cannot edit material outside your project"
                )

        changes: dict[str, object] = {}
        if command.project_is_set:
            changes["project"] = command.project
        if command.material_is_set:
            changes["material"] = command.material
        if command.quantity_is_set:
            changes["quantity"] = command.quantity
        price_is_set = command.price_is_set or command.price is not None
        if price_is_set:
            changes["price"] = command.price
        if price_is_set or command.quantity_is_set:
            price = command.price if price_is_set else current.price
            quantity = (
                command.quantity if command.quantity is not None else current.quantity
            )
            changes["summ"] = _calculate_summ(price, quantity)
        if command.project_work_is_set:
            changes["project_work"] = command.project_work

        if not changes:
            return current

        updated = current.with_updates(**changes)
        result = self.repository.update_project_material(updated)
        if result is None:
            raise ProjectMaterialNotFoundError("Project material not found")
        return result
