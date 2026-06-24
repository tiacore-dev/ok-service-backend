from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.users import User, UserNotFoundError

from .ports import UserRepository


@dataclass(slots=True)
class SoftDeleteUserUseCase:
    repository: UserRepository

    def execute(self, user_id: UUID) -> User:
        current = self.repository.get_user(user_id)
        if current is None:
            raise UserNotFoundError("User not found")
        result = self.repository.update_user(user_id, deleted=True)
        if result is None:
            raise UserNotFoundError("User not found")
        return result


@dataclass(slots=True)
class RestoreUserUseCase:
    repository: UserRepository

    def execute(self, user_id: UUID) -> User:
        current = self.repository.get_user(user_id)
        if current is None:
            raise UserNotFoundError("User not found")
        result = self.repository.update_user(user_id, deleted=False)
        if result is None:
            raise UserNotFoundError("User not found")
        return result


@dataclass(slots=True)
class DeleteUserUseCase:
    repository: UserRepository

    def execute(self, user_id: UUID) -> bool:
        current = self.repository.get_user(user_id)
        if current is None:
            raise UserNotFoundError("User not found")
        deleted = self.repository.delete_user(user_id)
        if not deleted:
            raise UserNotFoundError("User not found")
        return deleted
