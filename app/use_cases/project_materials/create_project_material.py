from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.domain.project_materials import ProjectMaterial

from .dto import CreateProjectMaterialCommand
from .ports import ProjectMaterialRepository
from ..time_utils import utc_epoch_milliseconds


@dataclass(slots=True)
class CreateProjectMaterialUseCase:
    repository: ProjectMaterialRepository

    def execute(self, command: CreateProjectMaterialCommand) -> ProjectMaterial:
        project_material = ProjectMaterial(
            project_material_id=uuid4(),
            project=command.project,
            material=command.material,
            quantity=command.quantity,
            created_by=command.created_by,
            created_at=utc_epoch_milliseconds(),
            project_work=command.project_work,
        )
        return self.repository.create_project_material(project_material)
