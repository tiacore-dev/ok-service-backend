from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.materials import MaterialNotFoundError

from .ports import MaterialRepository


@dataclass(slots=True)
class DeleteMaterialUseCase:
    repository: MaterialRepository

    def execute(self, material_id: UUID) -> bool:
        current = self.repository.get_material(material_id)
        if current is None:
            raise MaterialNotFoundError("Material not found")

        deleted = self.repository.delete_material(material_id)
        if not deleted:
            raise MaterialNotFoundError("Material not found")
        return deleted
