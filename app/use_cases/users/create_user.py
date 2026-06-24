from __future__ import annotations

from dataclasses import dataclass

from app.domain.users import User

from .dto import CreateUserCommand
from .ports import UserRepository


@dataclass(slots=True)
class CreateUserUseCase:
    repository: UserRepository

    def execute(self, command: CreateUserCommand) -> User:
        result = self.repository.create_user(command)
        if result is None:
            raise ValueError("User not found")
        return result
