from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from .errors import MaterialValidationError


@dataclass(frozen=True, slots=True)
class Material:
    material_id: UUID
    name: str
    measurement_unit: dict[str, Any] | UUID | None
    created_by: UUID
    created_at: int
    deleted: bool = False

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise MaterialValidationError("Material name is required.")
        if not isinstance(self.deleted, bool):
            raise MaterialValidationError("Material deleted flag must be boolean.")

    def with_updates(
        self,
        *,
        name: str | None = None,
        measurement_unit: dict[str, Any] | UUID | None = None,
        deleted: bool | None = None,
    ) -> Material:
        return Material(
            material_id=self.material_id,
            name=self.name if name is None else name,
            measurement_unit=self.measurement_unit
            if measurement_unit is None
            else measurement_unit,
            created_by=self.created_by,
            created_at=self.created_at,
            deleted=self.deleted if deleted is None else deleted,
        )
