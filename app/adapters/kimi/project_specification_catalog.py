from dataclasses import dataclass, field
from typing import Any

from app.adapters.materials import SQLAlchemyMaterialRepository
from app.adapters.works import SQLAlchemyWorkRepository
from app.use_cases.materials import MaterialListQuery
from app.use_cases.works import WorkListQuery


@dataclass(slots=True)
class SQLAlchemyProjectSpecificationCatalog:
    works: SQLAlchemyWorkRepository = field(default_factory=SQLAlchemyWorkRepository)
    materials: SQLAlchemyMaterialRepository = field(
        default_factory=SQLAlchemyMaterialRepository
    )

    def work_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "id": str(work.work_id),
                "name": work.name,
            }
            for work in self.works.list_works(WorkListQuery(limit=None, deleted=False))
        ]

    def material_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "id": str(material.material_id),
                "name": material.name,
            }
            for material in self.materials.list_materials(
                MaterialListQuery(limit=None, deleted=False)
            )
        ]
