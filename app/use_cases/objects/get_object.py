from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.objects import Object, ObjectForbiddenError, ObjectNotFoundError

from .dto import ObjectActor
from .ports import ObjectRepository


@dataclass(slots=True)
class GetObjectUseCase:
    repository: ObjectRepository

    def execute(self, object_id: UUID, actor: ObjectActor) -> Object:
        obj = self.repository.get_object(object_id)
        if obj is None:
            raise ObjectNotFoundError("Object not found")
        if actor.role == "user" and obj.status != "active":
            raise ObjectForbiddenError("Forbidden")
        return obj
