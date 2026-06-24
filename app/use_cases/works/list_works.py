from __future__ import annotations

from dataclasses import dataclass

from app.domain.works import Work

from .dto import WorkListQuery
from .ports import WorkRepository


@dataclass(slots=True)
class ListWorksUseCase:
    repository: WorkRepository

    def execute(self, query: WorkListQuery) -> list[Work]:
        return self.repository.list_works(query)
