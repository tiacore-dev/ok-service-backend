from __future__ import annotations

from dataclasses import dataclass

from app.domain.objects import Object, ObjectForbiddenError, ObjectNotFoundError

from .dto import ObjectActor, UpdateObjectCommand
from .ports import ObjectRepository


@dataclass(slots=True)
class UpdateObjectUseCase:
    repository: ObjectRepository

    def execute(self, command: UpdateObjectCommand, actor: ObjectActor) -> Object:
        current = self.repository.get_object(command.object_id)
        if current is None:
            raise ObjectNotFoundError("Object not found")
        if actor.role != "admin":
            raise ObjectForbiddenError("Forbidden")
        updated = current.with_updates(
            name=command.name,
            address=command.address,
            description=command.description,
            status=command.status,
            manager=command.manager,
            deleted=command.deleted,
            city_id=command.city,
            lng=command.lng,
            ltd=command.ltd,
        )
        result = (
            self.repository.update_object_with_projects_closed(updated)
            if command.status == "completed"
            else self.repository.update_object(updated)
        )
        if result is None:
            raise ObjectNotFoundError("Object not found")
        return result
