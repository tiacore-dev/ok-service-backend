from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.materials import Material

from .dto import MaterialListQuery


class MaterialRepository(Protocol):
    def create_material(self, material: Material) -> Material: ...

    def get_material(self, material_id: UUID) -> Material | None: ...

    def update_material(self, material: Material) -> Material | None: ...

    def delete_material(self, material_id: UUID) -> bool: ...

    def list_materials(self, query: MaterialListQuery) -> list[Material]: ...
