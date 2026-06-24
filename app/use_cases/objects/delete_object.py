from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.objects import ObjectForbiddenError, ObjectNotFoundError

from .dto import ObjectActor
from .ports import ObjectRepository


@dataclass(slots=True)
class SoftDeleteObjectUseCase:
    repository: ObjectRepository

    def execute(self, object_id: UUID, actor: ObjectActor) -> bool:
        current = self.repository.get_object(object_id)
        if current is None:
            raise ObjectNotFoundError("Object not found")
        if actor.role != "admin":
            raise ObjectForbiddenError("Forbidden")
        updated = current.with_updates(deleted=True)
        return self.repository.update_object(updated) is not None


@dataclass(slots=True)
class HardDeleteObjectUseCase:
    repository: ObjectRepository

    def execute(self, object_id: UUID, actor: ObjectActor) -> bool:
        current = self.repository.get_object(object_id)
        if current is None:
            raise ObjectNotFoundError("Object not found")
        if actor.role != "admin":
            raise ObjectForbiddenError("Forbidden")
        return self.repository.delete_object(object_id)
