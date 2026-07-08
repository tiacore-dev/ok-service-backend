from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .errors import UserValidationError


@dataclass(frozen=True, slots=True)
class User:
    user_id: UUID
    login: str
    name: str
    role: str
    category: int
    city: UUID | None
    created_by: UUID
    created_at: int
    deleted: bool
    position: UUID | None = None
    is_active: bool = True

    def __post_init__(self) -> None:
        if not str(self.login).strip():
            raise UserValidationError("User login is required.")
        if not str(self.name).strip():
            raise UserValidationError("User name is required.")
        if not str(self.role).strip():
            raise UserValidationError("User role is required.")
        if not isinstance(self.is_active, bool):
            raise UserValidationError("User active flag must be boolean.")
        if not isinstance(self.deleted, bool):
            raise UserValidationError("User deleted flag must be boolean.")

    def with_updates(
        self,
        *,
        login: str | None = None,
        name: str | None = None,
        role: str | None = None,
        category: int | None = None,
        city: UUID | None = None,
        position: UUID | None = None,
        is_active: bool | None = None,
        deleted: bool | None = None,
    ) -> User:
        return User(
            user_id=self.user_id,
            login=self.login if login is None else login,
            name=self.name if name is None else name,
            role=self.role if role is None else role,
            category=self.category if category is None else category,
            city=self.city if city is None else city,
            created_by=self.created_by,
            created_at=self.created_at,
            deleted=self.deleted if deleted is None else deleted,
            position=self.position if position is None else position,
            is_active=self.is_active if is_active is None else is_active,
        )
