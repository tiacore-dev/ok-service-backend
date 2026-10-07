from decimal import Decimal
from uuid import uuid4
from uuid import UUID

import pytest

from app.use_cases.project_specification_import import (
    ImportProjectSpecificationUseCase,
    ProjectMaterialImportItem,
    ProjectSpecificationImportActor,
    ProjectSpecificationImportCommand,
    ProjectSpecificationImportError,
    ProjectWorkImportItem,
)
from app.domain.project_materials import ProjectMaterial
from app.domain.project_works import ProjectWork

ImportCall = tuple[
    UUID,
    ProjectSpecificationImportActor,
    list[ProjectWork],
    list[ProjectMaterial],
]


class _Repository:
    def __init__(self, projects: list[UUID]):
        self.projects = projects
        self.called: ImportCall | None = None

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]:
        return self.projects

    def import_specification(
        self,
        project_id: UUID,
        actor: ProjectSpecificationImportActor,
        works: list[ProjectWork],
        materials: list[ProjectMaterial],
    ) -> None:
        self.called = (project_id, actor, works, materials)


def test_import_uses_path_project_and_calculates_sums():
    project_id, user_id, work_id, material_id, project_work_id = (uuid4() for _ in range(5))
    repository = _Repository([])
    command = ProjectSpecificationImportCommand(
        [ProjectWorkImportItem(project_work_id, "Work", work_id, Decimal("2"), Decimal("3"))],
        [ProjectMaterialImportItem(uuid4(), material_id, Decimal("4"), Decimal("5"), project_work_id)],
    )

    ImportProjectSpecificationUseCase(repository).execute(
        project_id, command, ProjectSpecificationImportActor(user_id, "manager")
    )

    assert repository.called is not None
    _, _, works, materials = repository.called
    assert works[0].project == project_id
    assert works[0].summ == Decimal("6")
    assert materials[0].project_work == project_work_id
    assert materials[0].summ == Decimal("20")


def test_import_rejects_material_reference_outside_payload():
    repository = _Repository([])
    command = ProjectSpecificationImportCommand(
        [],
        [ProjectMaterialImportItem(uuid4(), uuid4(), Decimal("1"), None, uuid4())],
    )

    with pytest.raises(ProjectSpecificationImportError, match="outside import"):
        ImportProjectSpecificationUseCase(repository).execute(
            uuid4(), command, ProjectSpecificationImportActor(uuid4(), "admin")
        )
