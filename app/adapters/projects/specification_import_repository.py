from dataclasses import dataclass
from uuid import UUID

from app.database import db_globals
from app.database.models import (
    Materials,
    ProjectMaterials,
    Projects,
    ProjectWorks,
    Works,
)
from app.domain.project_materials import ProjectMaterial
from app.domain.project_works import ProjectWork
from app.domain.projects import ProjectNotFoundError
from app.use_cases.project_specification_import import (
    ProjectSpecificationImportActor,
    ProjectSpecificationImportError,
    ProjectSpecificationImportRepository,
)


@dataclass(slots=True)
class SQLAlchemyProjectSpecificationImportRepository(
    ProjectSpecificationImportRepository
):
    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]:
        session_factory = db_globals.Session
        if session_factory is None:
            raise RuntimeError("Database session is not initialized")
        with session_factory() as session:
            return [
                row[0]
                for row in session.query(Projects.project_id)
                .filter(Projects.project_leader == user_id, Projects.deleted.is_(False))
                .all()
            ]

    def import_specification(
        self,
        project_id: UUID,
        actor: ProjectSpecificationImportActor,
        works: list[ProjectWork],
        materials: list[ProjectMaterial],
    ) -> None:
        session_factory = db_globals.Session
        if session_factory is None:
            raise RuntimeError("Database session is not initialized")
        with session_factory.begin() as session:
            project = session.get(Projects, project_id)
            if project is None or project.deleted:
                raise ProjectNotFoundError("Project not found")
            existing_work_ids = (
                {
                    row[0]
                    for row in session.query(ProjectWorks.project_work_id)
                    .filter(
                        ProjectWorks.project_work_id.in_(
                            [item.project_work_id for item in works]
                        )
                    )
                    .all()
                }
                if works
                else set()
            )
            existing_material_ids = (
                {
                    row[0]
                    for row in session.query(ProjectMaterials.project_material_id)
                    .filter(
                        ProjectMaterials.project_material_id.in_(
                            [item.project_material_id for item in materials]
                        )
                    )
                    .all()
                }
                if materials
                else set()
            )
            requested_ids = {item.project_work_id for item in works} | {
                item.project_material_id for item in materials
            }
            existing_ids = existing_work_ids | existing_material_ids
            if existing_ids:
                if existing_ids == requested_ids:
                    return
                raise ProjectSpecificationImportError(
                    "Import identifiers already exist"
                )
            work_catalog_ids = (
                {
                    row[0]
                    for row in session.query(Works.work_id)
                    .filter(
                        Works.work_id.in_([item.work for item in works]),
                        Works.deleted.is_(False),
                    )
                    .all()
                }
                if works
                else set()
            )
            material_catalog_ids = (
                {
                    row[0]
                    for row in session.query(Materials.material_id)
                    .filter(
                        Materials.material_id.in_(
                            [item.material for item in materials]
                        ),
                        Materials.deleted.is_(False),
                    )
                    .all()
                }
                if materials
                else set()
            )
            if len(work_catalog_ids) != len({item.work for item in works}) or len(
                material_catalog_ids
            ) != len({item.material for item in materials}):
                raise ProjectSpecificationImportError("Work or material not found")
            session.add_all(
                [
                    ProjectWorks(
                        project_work_id=item.project_work_id,
                        project_work_name=item.project_work_name,
                        project=item.project,
                        work=item.work,
                        quantity=item.quantity,
                        price=item.price,
                        summ=item.summ,
                        signed=item.signed,
                        created_by=item.created_by,
                        created_at=item.created_at,
                    )
                    for item in works
                ]
            )
            session.flush()
            session.add_all(
                [
                    ProjectMaterials(
                        project_material_id=item.project_material_id,
                        project=item.project,
                        material=item.material,
                        quantity=item.quantity,
                        price=item.price,
                        summ=item.summ,
                        project_work=item.project_work,
                        created_by=item.created_by,
                        created_at=item.created_at,
                    )
                    for item in materials
                ]
            )
