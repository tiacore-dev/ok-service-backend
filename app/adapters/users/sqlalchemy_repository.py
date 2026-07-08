from __future__ import annotations

from typing import cast
from uuid import UUID

from app.database.managers.user_manager import UserManager

from app.domain.users import User
from app.use_cases.users import CreateUserCommand, UserListQuery
from app.use_cases.users.ports import UserRepository

from .mappers import UserRecordDict, user_dict_to_entity


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session=None):
        self.manager = UserManager(session=session)

    def create_user(self, command: CreateUserCommand) -> User | None:
        self.manager.add_user(
            login=command.login,
            password=command.password,
            name=command.name,
            role=command.role,
            created_by=command.created_by,
            category=command.category if command.category is not None else 0,
            city=command.city,
            position=command.position,
            is_active=command.is_active,
        )
        with self.manager.session_scope() as session:
            record = (
                session.query(self.manager.model)
                .filter_by(login=command.login)
                .first()
            )
            return (
                user_dict_to_entity(cast(UserRecordDict, record.to_dict()))
                if record
                else None
            )

    def get_user(self, user_id: UUID) -> User | None:
        record = self.manager.get_by_id(user_id)
        return user_dict_to_entity(cast(UserRecordDict, record)) if record else None

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
    ) -> User | None:
        updated = self.manager.update(
            record_id=user_id,
            login=login,
            role=role,
            category=category,
            name=name,
            city_id=city,
            position_id=position,
            is_active=is_active,
            deleted=deleted,
        )
        if password is not None:
            password_result = self.manager.update_user_password(user_id, password)
            if password_result is False:
                return None
            updated = self.manager.get_by_id(user_id)
        elif updated is None:
            updated = self.manager.get_by_id(user_id)
        return user_dict_to_entity(cast(UserRecordDict, updated)) if updated else None

    def delete_user(self, user_id: UUID) -> bool:
        deleted = self.manager.delete(user_id)
        return bool(deleted)

    def list_users(self, query: UserListQuery) -> list[User]:
        records = self.manager.get_all_filtered(
            offset=query.offset,
            limit=query.limit,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            login=query.login,
            name=query.name,
            role=query.role,
            category=query.category,
            deleted=query.deleted,
            city_id=query.city,
            position_id=query.position,
            is_active=query.is_active,
        )
        return [user_dict_to_entity(cast(UserRecordDict, item)) for item in records]
