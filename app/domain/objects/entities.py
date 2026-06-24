from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID

from .errors import ObjectValidationError


@dataclass(frozen=True, slots=True)
class Object:
    object_id: UUID
    name: str
    address: str | None
    description: str | None
    city_id: UUID | None
    status: str | None
    manager: UUID | None
    lng: float | None
    ltd: float | None
    created_by: UUID | None
    created_at: int
    deleted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "address", None if self.address is None else str(self.address))
        object.__setattr__(
            self,
            "description",
            None if self.description is None else str(self.description),
        )
        object.__setattr__(self, "created_at", int(self.created_at))
        object.__setattr__(self, "deleted", bool(self.deleted))
        object.__setattr__(self, "lng", None if self.lng is None else float(self.lng))
        object.__setattr__(self, "ltd", None if self.ltd is None else float(self.ltd))
        if not self.name:
            raise ObjectValidationError("Object name is required.")

    def with_updates(
        self,
        *,
        name: str | None = None,
        address: str | None = None,
        description: str | None = None,
        city_id: UUID | None = None,
        status: str | None = None,
        manager: UUID | None = None,
        lng: float | None = None,
        ltd: float | None = None,
        deleted: bool | None = None,
    ) -> "Object":
        return replace(
            self,
            name=self.name if name is None else name,
            address=self.address if address is None else address,
            description=self.description if description is None else description,
            city_id=self.city_id if city_id is None else city_id,
            status=self.status if status is None else status,
            manager=self.manager if manager is None else manager,
            lng=self.lng if lng is None else lng,
            ltd=self.ltd if ltd is None else ltd,
            deleted=self.deleted if deleted is None else deleted,
        )
