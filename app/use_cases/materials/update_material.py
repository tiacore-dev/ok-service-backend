from __future__ import annotations

from dataclasses import dataclass

from app.domain.materials import Material, MaterialNotFoundError

from .dto import UpdateMaterialCommand
from .ports import MaterialRepository


@dataclass(slots=True)
class UpdateMaterialUseCase:
    repository: MaterialRepository

    def execute(self, command: UpdateMaterialCommand) -> Material:
        current = self.repository.get_material(command.material_id)
        if current is None:
            raise MaterialNotFoundError("Material not found")

        name = command.name
        measurement_unit = command.measurement_unit
        deleted = command.deleted

        if name is None and measurement_unit is None and deleted is None:
            return current

        updated = current.with_updates(
            name=name,
            measurement_unit=measurement_unit,
            deleted=deleted,
        )
        result = self.repository.update_material(updated)
        if result is None:
            raise MaterialNotFoundError("Material not found")
        return result
