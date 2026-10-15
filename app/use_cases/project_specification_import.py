from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.domain.project_materials import ProjectMaterial
from app.domain.project_works import ProjectWork
from app.domain.projects import ProjectForbiddenError
from app.use_cases.time_utils import utc_epoch_milliseconds


class ProjectSpecificationImportError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProjectSpecificationImportActor:
    user_id: UUID
    role: str


@dataclass(frozen=True, slots=True)
class ProjectWorkImportItem:
    project_work_id: UUID
    project_work_name: str
    work: UUID
    quantity: Decimal
    price: Decimal | None


@dataclass(frozen=True, slots=True)
class ProjectMaterialImportItem:
    project_material_id: UUID
    material: UUID
    quantity: Decimal
    price: Decimal | None
    project_work: UUID | None


@dataclass(frozen=True, slots=True)
class ProjectSpecificationImportCommand:
    project_works: list[ProjectWorkImportItem]
    project_materials: list[ProjectMaterialImportItem]


class ProjectSpecificationImportRepository(Protocol):
    def import_specification(
        self,
        project_id: UUID,
        actor: ProjectSpecificationImportActor,
        works: list[ProjectWork],
        materials: list[ProjectMaterial],
    ) -> None: ...

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]: ...


@dataclass(slots=True)
class ImportProjectSpecificationUseCase:
    repository: ProjectSpecificationImportRepository

    def execute(
        self,
        project_id: UUID,
        command: ProjectSpecificationImportCommand,
        actor: ProjectSpecificationImportActor,
    ) -> None:
        if actor.role == "project-leader" and project_id not in set(
            self.repository.get_project_ids_by_leader(actor.user_id)
        ):
            raise ProjectForbiddenError("You cannot import into this project")
        work_ids = [item.project_work_id for item in command.project_works]
        material_ids = [item.project_material_id for item in command.project_materials]
        if len(work_ids) != len(set(work_ids)) or len(material_ids) != len(set(material_ids)):
            raise ProjectSpecificationImportError("Duplicate import identifiers")
        work_id_set = set(work_ids)
        if any(
            item.project_work is not None and item.project_work not in work_id_set
            for item in command.project_materials
        ):
            raise ProjectSpecificationImportError("Material references a work outside import")
        now = utc_epoch_milliseconds()
        works = [
            ProjectWork(
                project_work_id=item.project_work_id,
                project_work_name=item.project_work_name,
                project=project_id,
                work=item.work,
                quantity=item.quantity,
                price=item.price,
                summ=item.price * item.quantity if item.price is not None else None,
                created_by=actor.user_id,
                created_at=now,
                signed=False,
            )
            for item in command.project_works
        ]
        materials = [
            ProjectMaterial(
                project_material_id=item.project_material_id,
                project=project_id,
                material=item.material,
                quantity=item.quantity,
                price=item.price,
                summ=item.price * item.quantity if item.price is not None else None,
                project_work=item.project_work,
                created_by=actor.user_id,
                created_at=now,
            )
            for item in command.project_materials
        ]
        self.repository.import_specification(project_id, actor, works, materials)
