from __future__ import annotations

from dataclasses import dataclass

from app.domain.objects import Object

from .dto import ObjectActor, ObjectListQuery
from .ports import ObjectRepository


@dataclass(slots=True)
class ListObjectsUseCase:
    repository: ObjectRepository

    def execute(self, query: ObjectListQuery, actor: ObjectActor) -> list[Object]:
        return self.repository.list_objects(query, actor)
