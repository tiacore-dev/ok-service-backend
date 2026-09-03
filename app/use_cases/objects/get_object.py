from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.objects import Object, ObjectForbiddenError, ObjectNotFoundError

from .dto import ObjectActor, ObjectStatsListQuery
from .ports import ObjectRepository


@dataclass(slots=True)
class GetObjectUseCase:
    repository: ObjectRepository

    def execute(self, object_id: UUID, actor: ObjectActor) -> Object:
        obj = self.repository.get_object(object_id)
        if obj is None:
            raise ObjectNotFoundError("Object not found")
        return obj


@dataclass(slots=True)
class GetObjectStatsUseCase:
    repository: ObjectRepository

    def execute(self, object_id: UUID, actor: ObjectActor) -> dict[str, object]:
        if actor.role == "user":
            raise ObjectForbiddenError("Forbidden")
        if self.repository.get_object(object_id) is None:
            raise ObjectNotFoundError("Object not found")
        return self.repository.get_object_stats(object_id)


@dataclass(slots=True)
class GetObjectStatsDetailsUseCase:
    repository: ObjectRepository

    def execute(self, object_id: UUID, actor: ObjectActor) -> dict[str, object]:
        if actor.role == "user":
            raise ObjectForbiddenError("Forbidden")
        if self.repository.get_object(object_id) is None:
            raise ObjectNotFoundError("Object not found")
        return self.repository.get_object_stats_details(object_id)


@dataclass(slots=True)
class GetAllObjectsStatsUseCase:
    repository: ObjectRepository

    def execute(self, query: ObjectStatsListQuery, actor: ObjectActor) -> dict[str, object]:
        if actor.role not in {"admin", "manager"}:
            raise ObjectForbiddenError("Forbidden")
        return self.repository.get_all_objects_stats(query)
