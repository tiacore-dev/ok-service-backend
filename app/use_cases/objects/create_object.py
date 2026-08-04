from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.domain.objects import Object
from app.use_cases.time_utils import utc_epoch_milliseconds

from .dto import CreateObjectCommand, ObjectActor
from .ports import ObjectRepository


@dataclass(slots=True)
class CreateObjectUseCase:
    repository: ObjectRepository

    def execute(self, command: CreateObjectCommand, actor: ObjectActor) -> Object:
        obj = Object(
            object_id=uuid4(),
            name=command.name,
            address=command.address,
            description=command.description,
            city_id=command.city,
            status=command.status,
            manager=command.manager,
            lng=command.lng,
            ltd=command.ltd,
            created_by=command.created_by or actor.user_id,
            created_at=utc_epoch_milliseconds(),
            deleted=False,
        )
        return self.repository.create_object(obj)
