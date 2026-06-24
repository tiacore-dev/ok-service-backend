from __future__ import annotations

from dataclasses import dataclass

from app.domain.materials import Material

from .dto import MaterialListQuery
from .ports import MaterialRepository


@dataclass(slots=True)
class ListMaterialsUseCase:
    repository: MaterialRepository

    def execute(self, query: MaterialListQuery) -> list[Material]:
        return self.repository.list_materials(query)
