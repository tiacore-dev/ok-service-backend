from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    login: str
    password: str
    name: str
    role: str
    category: int | None
    city: UUID
    created_by: UUID
    position: UUID | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class UpdateUserCommand:
    user_id: UUID
    login: str | None = None
    password: str | None = None
    name: str | None = None
    role: str | None = None
    category: int | None = None
    city: UUID | None = None
    position: UUID | None = None
    is_active: bool | None = None
    deleted: bool | None = None


@dataclass(frozen=True, slots=True)
class UserListQuery:
    offset: int = 0
    limit: int | None = 1000
    sort_by: str = "created_at"
    sort_order: str = "desc"
    login: str | None = None
    name: str | None = None
    role: str | None = None
    category: int | None = None
    city: UUID | None = None
    position: UUID | None = None
    is_active: bool | None = None
    deleted: bool | None = None
