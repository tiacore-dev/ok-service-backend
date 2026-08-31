from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.objects import Object

from .dto import ObjectActor, ObjectListQuery


class ObjectRepository(Protocol):
    def create_object(self, obj: Object) -> Object: ...

    def get_object(self, object_id: UUID) -> Object | None: ...

    def update_object(self, obj: Object) -> Object | None: ...

    def delete_object(self, object_id: UUID) -> bool: ...

    def list_objects(self, query: ObjectListQuery, actor: ObjectActor) -> list[Object]: ...

    def update_object_with_projects_closed(self, obj: Object) -> Object | None: ...
