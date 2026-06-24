from __future__ import annotations

from typing import TypedDict
from uuid import UUID

from app.domain.users import User


class UserRecordDict(TypedDict):
    user_id: str
    login: str
    name: str
    role: str
    category: int | None
    city: str | None
    created_by: str
    created_at: int
    deleted: bool


def user_dict_to_entity(data: UserRecordDict) -> User:
    city_value = data["city"]
    city = UUID(city_value) if city_value is not None else None
    return User(
        user_id=UUID(data["user_id"]),
        login=data["login"],
        name=data["name"],
        role=data["role"],
        category=data["category"] if data["category"] is not None else 0,
        city=city,
        created_by=UUID(data["created_by"]),
        created_at=data["created_at"],
        deleted=data["deleted"],
    )


def user_entity_to_response(user: User) -> dict[str, object]:
    return {
        "user_id": str(user.user_id),
        "login": user.login,
        "name": user.name,
        "role": user.role,
        "category": user.category if user.category else None,
        "city": str(user.city) if user.city else None,
        "created_by": str(user.created_by),
        "created_at": user.created_at,
        "deleted": user.deleted,
    }
