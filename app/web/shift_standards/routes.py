from __future__ import annotations

import json
import logging
from typing import Any, TypedDict, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.shift_standards import SQLAlchemyShiftStandardRepository
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.shift_standards import (
    ShiftStandardNotFoundError,
    ShiftStandardValidationError,
)
from app.routes.models.shift_standard_models import (
    shift_standard_all_response,
    shift_standard_create_model,
    shift_standard_edit_model,
    shift_standard_filter_parser,
    shift_standard_model,
    shift_standard_msg_model,
    shift_standard_response,
)
from app.schemas.shift_standard_schemas import (
    ShiftStandardCreateSchema,
    ShiftStandardEditSchema,
    ShiftStandardFilterSchema,
)
from app.use_cases.shift_standards import (
    CreateShiftStandardCommand,
    CreateShiftStandardUseCase,
    DeleteShiftStandardUseCase,
    GetShiftStandardUseCase,
    ListShiftStandardsUseCase,
    ShiftStandardListQuery,
    UpdateShiftStandardCommand,
    UpdateShiftStandardUseCase,
)
from app.web._typing import required_uuid, to_plain_dict

shift_standard_ns = Namespace(
    "shift_standards", description="Shift standard reference operations"
)
logger = logging.getLogger("ok_service")
for model in (
    shift_standard_create_model,
    shift_standard_edit_model,
    shift_standard_msg_model,
    shift_standard_response,
    shift_standard_all_response,
    shift_standard_model,
):
    shift_standard_ns.models[model.name] = model


class _CreatePayload(TypedDict):
    category: int
    standard: float
    notification_text: str | None


class _EditPayload(TypedDict, total=False):
    category: int
    standard: float
    notification_text: str | None


def _id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _current_user() -> dict[str, Any]:
    identity = (
        getattr(g, "api_key_identity_json", None)
        if getattr(g, "auth_via_api_key", False)
        else _get_jwt_identity()
    )
    if isinstance(identity, dict):
        return identity
    if isinstance(identity, (str, bytes, bytearray)):
        try:
            parsed = json.loads(identity)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _response(item) -> dict[str, Any]:
    return {
        "shift_standard_id": str(item.shift_standard_id),
        "category": item.category,
        "standard": item.standard,
        "notification_text": item.notification_text,
        "created_at": item.created_at,
        "created_by": str(item.created_by),
    }


def _error(error: Exception):
    if isinstance(error, ShiftStandardNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, ShiftStandardValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Shift standard category must be unique."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    logger.exception("Shift standard request failed")
    return {"msg": "Internal server error"}, 500


@shift_standard_ns.route("/add")
class ShiftStandardAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @shift_standard_ns.expect(shift_standard_create_model, validate=False)
    def post(self):
        try:
            raw = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(_CreatePayload, ShiftStandardCreateSchema().load(raw))
            item = CreateShiftStandardUseCase(
                SQLAlchemyShiftStandardRepository()
            ).execute(
                CreateShiftStandardCommand(
                    category=data["category"],
                    standard=data["standard"],
                    notification_text=data.get("notification_text"),
                    created_by=required_uuid(
                        _current_user().get("user_id"), "Current user id is required"
                    ),
                )
            )
            return {
                "msg": "New shift standard added successfully",
                "shift_standard_id": str(item.shift_standard_id),
            }, 200
        except Exception as error:
            return _error(error)


@shift_standard_ns.route("/<string:shift_standard_id>/view")
class ShiftStandardView(Resource):
    @api_key_or_jwt_required
    def get(self, shift_standard_id):
        try:
            item = GetShiftStandardUseCase(SQLAlchemyShiftStandardRepository()).execute(
                _id(shift_standard_id)
            )
            return {
                "msg": "Shift standard found successfully",
                "shift_standard": _response(item),
            }, 200
        except Exception as error:
            return _error(error)


@shift_standard_ns.route("/<string:shift_standard_id>/edit")
class ShiftStandardEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @shift_standard_ns.expect(shift_standard_edit_model, validate=False)
    def patch(self, shift_standard_id):
        try:
            raw = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(_EditPayload, ShiftStandardEditSchema().load(raw))
            if not data:
                raise ValueError("No data provided for update")
            item = UpdateShiftStandardUseCase(
                SQLAlchemyShiftStandardRepository()
            ).execute(
                UpdateShiftStandardCommand(
                    shift_standard_id=_id(shift_standard_id),
                    category=data.get("category"),
                    standard=data.get("standard"),
                    notification_text=data.get("notification_text"),
                    notification_text_provided="notification_text" in raw,
                )
            )
            return {
                "msg": "Shift standard edited successfully",
                "shift_standard_id": str(item.shift_standard_id),
            }, 200
        except Exception as error:
            return _error(error)


@shift_standard_ns.route("/<string:shift_standard_id>/delete/hard")
class ShiftStandardDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    def delete(self, shift_standard_id):
        try:
            DeleteShiftStandardUseCase(SQLAlchemyShiftStandardRepository()).execute(
                _id(shift_standard_id)
            )
            return {
                "msg": "Shift standard deleted successfully",
                "shift_standard_id": shift_standard_id,
            }, 200
        except Exception as error:
            return _error(error)


@shift_standard_ns.route("/all")
class ShiftStandardAll(Resource):
    @api_key_or_jwt_required
    @shift_standard_ns.expect(shift_standard_filter_parser)
    def get(self):
        try:
            raw = to_plain_dict(request.args, "Request query is required")
            data = cast(dict[str, Any], ShiftStandardFilterSchema().load(raw))
            category = data.get("category")
            items = ListShiftStandardsUseCase(
                SQLAlchemyShiftStandardRepository()
            ).execute(
                ShiftStandardListQuery(
                    offset=int(data.get("offset", 0)),
                    limit=int(data.get("limit", 1000)),
                    category=int(category) if category is not None else None,
                )
            )
            return {
                "msg": "Shift standards found successfully",
                "shift_standards": [_response(item) for item in items],
            }, 200
        except Exception as error:
            return _error(error)
