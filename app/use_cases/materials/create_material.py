from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.database.time_utils import utc_epoch_seconds
from app.domain.materials import Material

from .dto import CreateMaterialCommand
from .ports import MaterialRepository


@dataclass(slots=True)
class CreateMaterialUseCase:
    repository: MaterialRepository

    def execute(self, command: CreateMaterialCommand) -> Material:
        material = Material(
            material_id=uuid4(),
            name=command.name,
            measurement_unit=command.measurement_unit,
            created_by=command.created_by,
            created_at=utc_epoch_seconds(),
            deleted=False,
        )
        return self.repository.create_material(material)
