from __future__ import annotations

import json
from typing import Any, TypedDict, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.acceptances import SQLAlchemyAcceptanceRepository
from app.decorators import admin_or_manager_required, api_key_or_jwt_required
from app.domain.acceptances import AcceptanceStatus, AcceptanceForbiddenError, AcceptanceNotFoundError, AcceptanceValidationError
from app.routes.models.acceptance_models import acceptance_all_response, acceptance_create_model, acceptance_edit_model, acceptance_filter_parser, acceptance_model, acceptance_msg_model, acceptance_response
from app.schemas.acceptance_schemas import AcceptanceCreateSchema, AcceptanceEditSchema, AcceptanceFilterSchema
from app.use_cases.acceptances import AcceptanceActor, AcceptanceListQuery, CreateAcceptanceCommand, CreateAcceptanceUseCase, DeleteAcceptanceUseCase, GetAcceptanceUseCase, ListAcceptancesUseCase, UpdateAcceptanceCommand, UpdateAcceptanceUseCase
from app.web._typing import get_optional_int, get_optional_str, get_required_int, get_required_str, get_required_uuid, optional_uuid

acceptance_ns = Namespace("acceptances", description="Acceptances management operations")
for model in (acceptance_create_model, acceptance_edit_model, acceptance_model, acceptance_msg_model, acceptance_response, acceptance_all_response):
    acceptance_ns.models[model.name] = model


class AcceptanceCreatePayload(TypedDict):
    date: int
    project_id: str
    status: str
    comment: str | None


class AcceptanceEditPayload(TypedDict, total=False):
    date: int | None
    project_id: str | None
    status: str | None
    comment: str | None


class AcceptanceFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    project_id: str
    status: str


def _user() -> dict[str, Any]:
    identity = getattr(g, "api_key_identity_json", None) if getattr(g, "auth_via_api_key", False) else get_jwt_identity()
    if isinstance(identity, dict):
        return identity
    if isinstance(identity, (str, bytes, bytearray)):
        try:
            value = json.loads(identity)
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def _id(value: str) -> UUID:
    return get_required_uuid({"id": value}, "id", "Invalid UUID format")


def _actor(user: dict[str, Any]) -> AcceptanceActor:
    return AcceptanceActor(role=str(user.get("role", "")))


def _repo() -> SQLAlchemyAcceptanceRepository:
    return SQLAlchemyAcceptanceRepository()


def _json_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("Request body is required")
    return cast(dict[str, Any], payload)


def _response(item):
    return {"id": str(item.id), "date": item.date, "project_id": str(item.project_id), "status": item.status.value, "comment": item.comment}


def _error(error: Exception):
    if isinstance(error, AcceptanceNotFoundError): return {"msg": str(error)}, 404
    if isinstance(error, AcceptanceForbiddenError): return {"msg": str(error)}, 403
    if isinstance(error, (AcceptanceValidationError, ValidationError, ValueError)): return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError): return {"msg": "Cannot delete acceptance: dependent data exists."}, 409
    return {"msg": f"Internal error: {error}"}, 500


@acceptance_ns.route("/add")
class AcceptanceAdd(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @acceptance_ns.expect(acceptance_create_model, validate=False)
    @acceptance_ns.marshal_with(acceptance_msg_model)
    def post(self):
        try:
            user = _user(); data = cast(AcceptanceCreatePayload, AcceptanceCreateSchema().load(_json_payload()))
            item = CreateAcceptanceUseCase(_repo()).execute(CreateAcceptanceCommand(
                date=get_required_int(data, "date", "Date is required"),
                project_id=get_required_uuid(data, "project_id", "Project id is required"),
                status=AcceptanceStatus(get_required_str(data, "status", "Status is required")),
                comment=get_optional_str(data, "comment")), _actor(user))
            return {"msg": "Acceptance added successfully", "id": str(item.id)}, 200
        except Exception as error: return _error(error)


@acceptance_ns.route("/<string:acceptance_id>/view")
class AcceptanceView(Resource):
    @api_key_or_jwt_required
    @acceptance_ns.marshal_with(acceptance_response)
    def get(self, acceptance_id):
        try: return {"msg": "Acceptance found successfully", "acceptance": _response(GetAcceptanceUseCase(_repo()).execute(_id(acceptance_id)))}, 200
        except Exception as error: return _error(error)


@acceptance_ns.route("/<string:acceptance_id>/edit")
class AcceptanceEdit(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @acceptance_ns.expect(acceptance_edit_model, validate=False)
    @acceptance_ns.marshal_with(acceptance_msg_model)
    def patch(self, acceptance_id):
        try:
            user = _user(); data = cast(AcceptanceEditPayload, AcceptanceEditSchema().load(_json_payload()))
            item = UpdateAcceptanceUseCase(_repo()).execute(UpdateAcceptanceCommand(
                id=_id(acceptance_id), date=get_optional_int(data, "date"), project_id=optional_uuid(get_optional_str(data, "project_id")),
                status=AcceptanceStatus(get_optional_str(data, "status")) if get_optional_str(data, "status") else None,
                comment=get_optional_str(data, "comment"), comment_provided="comment" in data), _actor(user))
            return {"msg": "Acceptance edited successfully", "id": str(item.id)}, 200
        except Exception as error: return _error(error)


@acceptance_ns.route("/<string:acceptance_id>/delete/hard")
class AcceptanceDelete(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @acceptance_ns.marshal_with(acceptance_msg_model)
    def delete(self, acceptance_id):
        try:
            deleted = DeleteAcceptanceUseCase(_repo()).execute(_id(acceptance_id), _actor(_user()))
            if not deleted: raise AcceptanceNotFoundError("Acceptance not found")
            return {"msg": "Acceptance deleted successfully", "id": acceptance_id}, 200
        except Exception as error: return _error(error)


@acceptance_ns.route("/all")
class AcceptanceAll(Resource):
    @api_key_or_jwt_required
    @acceptance_ns.expect(acceptance_filter_parser)
    @acceptance_ns.marshal_with(acceptance_all_response)
    def get(self):
        try:
            data = cast(AcceptanceFilterPayload, AcceptanceFilterSchema().load(request.args.to_dict()))
            status = data.get("status")
            items = ListAcceptancesUseCase(_repo()).execute(AcceptanceListQuery(
                offset=data.get("offset", 0), limit=data.get("limit", 1000),
                project_id=optional_uuid(data.get("project_id")),
                status=AcceptanceStatus(status) if status else None))
            return {"msg": "Acceptances found successfully", "acceptances": [_response(item) for item in items]}, 200
        except Exception as error: return _error(error)
