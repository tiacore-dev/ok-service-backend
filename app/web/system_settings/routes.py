import json
from typing import Any, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError

from app.adapters.system_settings import (
    SQLAlchemySystemSettingRepository,
    system_setting_entity_to_response,
)
from app.decorators import admin_required, api_key_or_jwt_required
from app.schemas.system_setting_schemas import SystemSettingEditSchema
from app.use_cases.system_settings import (
    GetSystemSettingUseCase,
    ListSystemSettingsUseCase,
    UpdateSystemSettingCommand,
    UpdateSystemSettingUseCase,
)
from app.web._typing import to_plain_dict

from .models import (
    system_setting_all_response,
    system_setting_edit_model,
    system_setting_model,
    system_setting_response,
)

system_setting_ns = Namespace(
    "system_settings", description="System settings reference operations"
)
for model in (
    system_setting_model,
    system_setting_response,
    system_setting_all_response,
    system_setting_edit_model,
):
    system_setting_ns.models[model.name] = model


def _repository() -> SQLAlchemySystemSettingRepository:
    return SQLAlchemySystemSettingRepository()


def _id(value: str) -> str:
    if not value:
        raise ValueError("System setting id is required")
    return value


def _error(error: Exception):
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"System setting operation failed: {error}"}, 500


def _current_user_id() -> UUID:
    identity: Any = (
        getattr(g, "api_key_identity_json", None)
        if getattr(g, "auth_via_api_key", False)
        else get_jwt_identity()
    )
    if isinstance(identity, (str, bytes, bytearray)):
        identity = json.loads(identity)
    if not isinstance(identity, dict) or not identity.get("user_id"):
        raise ValueError("Current user id is required")
    return UUID(str(identity["user_id"]))


@system_setting_ns.route("/all")
class SystemSettingAll(Resource):
    @api_key_or_jwt_required
    @system_setting_ns.response(200, "Success", system_setting_all_response)
    def get(self):
        try:
            settings = ListSystemSettingsUseCase(_repository()).execute()
            return {
                "msg": "System settings found successfully",
                "system_settings": [
                    system_setting_entity_to_response(setting) for setting in settings
                ],
            }, 200
        except Exception as error:
            return _error(error)


@system_setting_ns.route("/<string:system_setting_id>/view")
class SystemSettingView(Resource):
    @api_key_or_jwt_required
    @system_setting_ns.response(200, "Success", system_setting_response)
    def get(self, system_setting_id: str):
        try:
            setting = GetSystemSettingUseCase(_repository()).execute(
                _id(system_setting_id)
            )
            if setting is None:
                return {"msg": "System setting not found"}, 404
            return {
                "msg": "System setting found successfully",
                "system_setting": system_setting_entity_to_response(setting),
            }, 200
        except Exception as error:
            return _error(error)


@system_setting_ns.route("/<string:system_setting_id>/edit")
class SystemSettingEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @system_setting_ns.expect(system_setting_edit_model, validate=False)
    @system_setting_ns.response(200, "Success", system_setting_response)
    def patch(self, system_setting_id: str):
        try:
            data = cast(
                dict[str, str | None],
                SystemSettingEditSchema().load(
                    to_plain_dict(
                        request.get_json(silent=True), "Request body is required"
                    )
                ),
            )
            setting = UpdateSystemSettingUseCase(_repository()).execute(
                UpdateSystemSettingCommand(
                    _id(system_setting_id), data["value"], _current_user_id()
                )
            )
            if setting is None:
                return {"msg": "System setting not found"}, 404
            return {
                "msg": "System setting edited successfully",
                "system_setting": system_setting_entity_to_response(setting),
            }, 200
        except Exception as error:
            return _error(error)
