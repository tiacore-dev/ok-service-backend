from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.users import User

from .dto import CreateUserCommand, UserListQuery


class UserRepository(Protocol):
    def create_user(self, command: CreateUserCommand) -> User | None: ...

    def get_user(self, user_id: UUID) -> User | None: ...

    def update_user(
        self,
        user_id: UUID,
        *,
        login: str | None = None,
        password: str | None = None,
        name: str | None = None,
        role: str | None = None,
        category: int | None = None,
        city: UUID | None = None,
        position: UUID | None = None,
        is_active: bool | None = None,
        deleted: bool | None = None,
    ) -> User | None: ...

    def delete_user(self, user_id: UUID) -> bool: ...

    def list_users(self, query: UserListQuery) -> list[User]: ...
