from __future__ import annotations

from dataclasses import dataclass

from app.domain.object_statuses import ObjectStatus

from .dto import ObjectStatusListQuery
from .ports import ObjectStatusRepository


@dataclass(slots=True)
class ListObjectStatusesUseCase:
    repository: ObjectStatusRepository

    def execute(self, query: ObjectStatusListQuery) -> list[ObjectStatus]:
        return self.repository.list_object_statuses(query)
