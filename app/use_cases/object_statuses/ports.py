from __future__ import annotations

from typing import Protocol

from app.domain.object_statuses import ObjectStatus

from .dto import ObjectStatusListQuery


class ObjectStatusRepository(Protocol):
    def list_object_statuses(self, query: ObjectStatusListQuery) -> list[ObjectStatus]: ...
