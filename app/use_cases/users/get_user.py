from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.users import User, UserNotFoundError

from .ports import UserRepository


@dataclass(slots=True)
class GetUserUseCase:
    repository: UserRepository

    def execute(self, user_id: UUID) -> User:
        result = self.repository.get_user(user_id)
        if result is None:
            raise UserNotFoundError("User not found")
        return result
