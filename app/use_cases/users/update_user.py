from __future__ import annotations

from dataclasses import dataclass

from app.domain.users import User, UserNotFoundError

from .dto import UpdateUserCommand
from .ports import UserRepository


@dataclass(slots=True)
class UpdateUserUseCase:
    repository: UserRepository

    def execute(self, command: UpdateUserCommand) -> User:
        current = self.repository.get_user(command.user_id)
        if current is None:
            raise UserNotFoundError("User not found")

        if (
            command.login is None
            and command.password is None
            and command.name is None
            and command.role is None
            and command.category is None
            and command.city is None
            and command.deleted is None
        ):
            return current

        result = self.repository.update_user(
            command.user_id,
            login=command.login,
            password=command.password,
            name=command.name,
            role=command.role,
            category=command.category,
            city=command.city,
            deleted=command.deleted,
        )
        if result is None:
            raise UserNotFoundError("User not found")
        return result
