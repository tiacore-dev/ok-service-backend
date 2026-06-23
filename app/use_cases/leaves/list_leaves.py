from __future__ import annotations

from dataclasses import dataclass

from app.domain.leaves import Leave

from .dto import LeaveListQuery
from .ports import LeaveRepository


@dataclass(slots=True)
class ListLeavesUseCase:
    repository: LeaveRepository

    def execute(self, query: LeaveListQuery) -> list[Leave]:
        return self.repository.list_leaves(query)

