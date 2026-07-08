from __future__ import annotations

import json
import logging
from typing import Any, NotRequired, TypedDict, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.users import (
    SQLAlchemyUserRepository,
    user_entity_to_response,
)
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.users import UserNotFoundError
from app.routes.models.user_models import (
    user_all_response,
    user_create_model,
    user_edit_model,
    user_filter_parser,
    user_model,
    user_msg_model,
    user_response,
)
from app.schemas.user_schemas import UserCreateSchema, UserEditSchema, UserFilterSchema
from app.use_cases.users import (
    CreateUserCommand,
    CreateUserUseCase,
    DeleteUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    RestoreUserUseCase,
    SoftDeleteUserUseCase,
    UpdateUserCommand,
    UpdateUserUseCase,
    UserListQuery,
)
from app.web._typing import (
    get_optional_bool,
    get_optional_int,
    get_optional_str,
    get_optional_uuid,
    get_required_uuid,
    to_plain_dict,
)

logger = logging.getLogger("ok_service")

user_ns = Namespace("users", description="User management operations")

user_ns.models[user_create_model.name] = user_create_model
user_ns.models[user_edit_model.name] = user_edit_model
user_ns.models[user_msg_model.name] = user_msg_model
user_ns.models[user_all_response.name] = user_all_response
user_ns.models[user_response.name] = user_response
user_ns.models[user_model.name] = user_model


class UserCreatePayload(TypedDict):
    login: str
    password: str
    name: str
    role: str
    city: str
    category: NotRequired[int | None]
    position: NotRequired[str | None]
    is_active: NotRequired[bool]


class UserEditPayload(TypedDict, total=False):
    login: str
    password: str
    name: str
    role: str
    category: int | None
    deleted: bool
    city: str | None
    position: str | None
    is_active: bool | None


class UserFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    login: str
    name: str
    role: str
    category: int
    city: str
    position: str
    is_active: bool
    deleted: bool


def get_jwt_identity():
    if getattr(g, "auth_via_api_key", False):
        return getattr(g, "api_key_identity_json", None)
    return _get_jwt_identity()


def _get_current_user() -> dict[str, Any]:
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return identity
    if isinstance(identity, (str, bytes, bytearray)):
        try:
            parsed = json.loads(identity)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _repository() -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository()


def _parse_user_id(user_id: str) -> UUID:
    try:
        return UUID(user_id)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _forbid_api_key_admin_target(user: dict[str, Any] | None) -> bool:
    return bool(
        getattr(g, "auth_via_api_key", False) and user and user.get("role") == "admin"
    )


def _map_error(error: Exception):
    if isinstance(error, UserNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete user: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@user_ns.route("/add")
class UserAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @user_ns.expect(user_create_model, validate=False)
    @user_ns.marshal_with(user_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new user", extra={"login": current_user})

        schema = UserCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(UserCreatePayload, schema.load(raw_payload))
            is_active = get_optional_bool(data, "is_active")
            user = CreateUserUseCase(repository=_repository()).execute(
                CreateUserCommand(
                    login=data["login"],
                    password=data["password"],
                    name=data["name"],
                    role=data["role"],
                    category=get_optional_int(data, "category"),
                    city=get_required_uuid(data, "city", "City is required"),
                    created_by=get_required_uuid(
                        current_user, "user_id", "Current user id is required"
                    ),
                    position=get_optional_uuid(data, "position"),
                    is_active=True if is_active is None else is_active,
                )
            )
            return {
                "msg": "New user added successfully",
                "user_id": str(user.user_id),
            }, 200
        except Exception as error:
            logger.error(f"Error adding user: {error}", extra={"login": current_user})
            return _map_error(error)


@user_ns.route("/<string:user_id>/view")
class UserView(Resource):
    @api_key_or_jwt_required
    @user_ns.marshal_with(user_response)
    def get(self, user_id):
        current_user = _get_current_user()
        logger.info(f"Request to view user: {user_id}", extra={"login": current_user})
        try:
            user = GetUserUseCase(repository=_repository()).execute(
                _parse_user_id(user_id)
            )
            return {
                "msg": "User found successfully",
                "user": user_entity_to_response(user),
            }, 200
        except Exception as error:
            logger.error(f"Error viewing user: {error}", extra={"login": current_user})
            return _map_error(error)


@user_ns.route("/<string:user_id>/delete/soft")
class UserSoftDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @user_ns.marshal_with(user_msg_model)
    def patch(self, user_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to soft delete user: {user_id}",
            extra={"login": current_user},
        )
        try:
            target = _repository().get_user(_parse_user_id(user_id))
            if target is None:
                raise UserNotFoundError("User not found")
            if _forbid_api_key_admin_target(user_entity_to_response(target)):
                return {"msg": "Forbidden"}, 403
            user = SoftDeleteUserUseCase(repository=_repository()).execute(
                _parse_user_id(user_id)
            )
            return {
                "msg": f"User {user.user_id} soft deleted successfully",
                "user_id": str(user.user_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error soft deleting user: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@user_ns.route("/<string:user_id>/restore")
class UserRestore(Resource):
    @api_key_or_jwt_required
    @admin_required
    @user_ns.marshal_with(user_msg_model)
    def patch(self, user_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to restore user: {user_id}", extra={"login": current_user}
        )
        try:
            target = _repository().get_user(_parse_user_id(user_id))
            if target is None:
                raise UserNotFoundError("User not found")
            if _forbid_api_key_admin_target(user_entity_to_response(target)):
                return {"msg": "Forbidden"}, 403
            user = RestoreUserUseCase(repository=_repository()).execute(
                _parse_user_id(user_id)
            )
            return {
                "msg": f"User {user.user_id} restored successfully",
                "user_id": str(user.user_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error restoring user: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@user_ns.route("/<string:user_id>/delete/hard")
class UserHardDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @user_ns.marshal_with(user_msg_model)
    def delete(self, user_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete user: {user_id}",
            extra={"login": current_user},
        )
        try:
            user_id_value = _parse_user_id(user_id)
            target = _repository().get_user(user_id_value)
            if target is None:
                raise UserNotFoundError("User not found")
            if _forbid_api_key_admin_target(user_entity_to_response(target)):
                return {"msg": "Forbidden"}, 403
            if target.created_by == target.user_id:
                return {"msg": "You cannot delete admin"}, 403
            deleted = DeleteUserUseCase(repository=_repository()).execute(user_id_value)
            if not deleted:
                raise UserNotFoundError("User not found")
            return {
                "msg": f"User {user_id} hard deleted successfully",
                "user_id": user_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting user: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@user_ns.route("/<string:user_id>/edit")
class UserEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @user_ns.expect(user_edit_model, validate=False)
    @user_ns.marshal_with(user_msg_model)
    def patch(self, user_id):
        current_user = _get_current_user()
        logger.info(f"Request to edit user: {user_id}", extra={"login": current_user})

        schema = UserEditSchema()
        try:
            user_id_value = _parse_user_id(user_id)
            target = _repository().get_user(user_id_value)
            if target is None:
                raise UserNotFoundError("User not found")
            if _forbid_api_key_admin_target(user_entity_to_response(target)):
                return {"msg": "Forbidden"}, 403

            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(UserEditPayload, schema.load(raw_payload))

            login = get_optional_str(data, "login")
            password = get_optional_str(data, "password")
            name = get_optional_str(data, "name")
            role = get_optional_str(data, "role")
            category = get_optional_int(data, "category")
            deleted = get_optional_bool(data, "deleted")
            city = get_optional_uuid(data, "city")
            position = get_optional_uuid(data, "position")
            is_active = get_optional_bool(data, "is_active")

            if not any(value is not None for value in data.values()):
                return {"msg": "Bad request, invalid data."}, 400

            user = UpdateUserUseCase(repository=_repository()).execute(
                UpdateUserCommand(
                    user_id=user_id_value,
                    login=login,
                    password=password,
                    name=name,
                    role=role,
                    category=category,
                    city=city,
                    position=position,
                    is_active=is_active,
                    deleted=deleted,
                )
            )
            return {
                "msg": "User edited successfully",
                "user_id": str(user.user_id),
            }, 200
        except Exception as error:
            logger.error(f"Error editing user: {error}", extra={"login": current_user})
            return _map_error(error)


@user_ns.route("/all")
class UserAll(Resource):
    @api_key_or_jwt_required
    @user_ns.expect(user_filter_parser)
    @user_ns.marshal_with(user_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all users", extra={"login": current_user})

        schema = UserFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            data = cast(UserFilterPayload, schema.load(raw_args))
            users = ListUsersUseCase(repository=_repository()).execute(
                UserListQuery(
                    offset=get_optional_int(data, "offset") or 0,
                    limit=get_optional_int(data, "limit"),
                    sort_by=get_optional_str(data, "sort_by") or "created_at",
                    sort_order=get_optional_str(data, "sort_order") or "desc",
                    login=get_optional_str(data, "login"),
                    name=get_optional_str(data, "name"),
                    role=get_optional_str(data, "role"),
                    category=get_optional_int(data, "category"),
                    city=get_optional_uuid(data, "city"),
                    position=get_optional_uuid(data, "position"),
                    is_active=get_optional_bool(data, "is_active"),
                    deleted=get_optional_bool(data, "deleted"),
                )
            )
            return {
                "msg": "Users found successfully",
                "users": [user_entity_to_response(item) for item in users],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching users: {error}", extra={"login": current_user}
            )
            return _map_error(error)
