from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.materials import Material, MaterialNotFoundError

from .ports import MaterialRepository


@dataclass(slots=True)
class GetMaterialUseCase:
    repository: MaterialRepository

    def execute(self, material_id: UUID) -> Material:
        material = self.repository.get_material(material_id)
        if material is None:
            raise MaterialNotFoundError("Material not found")
        return material
