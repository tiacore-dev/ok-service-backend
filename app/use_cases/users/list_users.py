from __future__ import annotations

from dataclasses import dataclass

from app.domain.users import User

from .dto import UserListQuery
from .ports import UserRepository


@dataclass(slots=True)
class ListUsersUseCase:
    repository: UserRepository

    def execute(self, query: UserListQuery) -> list[User]:
        return self.repository.list_users(query)
