from __future__ import annotations

import json
from typing import Any, NotRequired, TypedDict, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.measurement_units import SQLAlchemyMeasurementUnitRepository
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.measurement_units import MeasurementUnitNotFoundError, MeasurementUnitValidationError
from app.routes.models.measurement_unit_models import (
    measurement_unit_all_response, measurement_unit_create_model, measurement_unit_edit_model,
    measurement_unit_filter_parser, measurement_unit_model, measurement_unit_msg_model,
    measurement_unit_response,
)
from app.schemas.measurement_unit_schemas import MeasurementUnitCreateSchema, MeasurementUnitEditSchema, MeasurementUnitFilterSchema
from app.use_cases.measurement_units import (
    CreateMeasurementUnitCommand, CreateMeasurementUnitUseCase, DeleteMeasurementUnitUseCase,
    GetMeasurementUnitUseCase, ListMeasurementUnitsUseCase, MeasurementUnitListQuery,
    UpdateMeasurementUnitCommand, UpdateMeasurementUnitUseCase,
)
from app.web._typing import required_uuid, to_plain_dict

measurement_unit_ns = Namespace("measurement_units", description="Measurement unit reference operations")
for model in (measurement_unit_create_model, measurement_unit_edit_model, measurement_unit_msg_model, measurement_unit_response, measurement_unit_all_response, measurement_unit_model):
    measurement_unit_ns.models[model.name] = model


class _CreatePayload(TypedDict):
    name: str


class _EditPayload(TypedDict):
    name: str


class _FilterPayload(TypedDict):
    offset: int
    limit: int
    name: NotRequired[str]


def _identity() -> dict[str, Any]:
    value = getattr(g, "api_key_identity_json", None) if getattr(g, "auth_via_api_key", False) else _get_jwt_identity()
    if isinstance(value, dict):
        return value
    if isinstance(value, (str, bytes, bytearray)):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def _id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _error(error: Exception):
    if isinstance(error, MeasurementUnitNotFoundError): return {"msg": str(error)}, 404
    if isinstance(error, MeasurementUnitValidationError): return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError): return {"msg": "Cannot delete measurement unit: dependent data exists."}, 409
    if isinstance(error, ValidationError): return {"error": error.messages}, 400
    if isinstance(error, ValueError): return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


def _response(item):
    return {"measurement_unit_id": str(item.measurement_unit_id), "name": item.name, "created_at": item.created_at, "created_by": str(item.created_by) if item.created_by is not None else None}


@measurement_unit_ns.route("/add")
class MeasurementUnitAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @measurement_unit_ns.expect(measurement_unit_create_model, validate=False)
    @measurement_unit_ns.marshal_with(measurement_unit_msg_model)
    def post(self):
        try:
            data = cast(_CreatePayload, MeasurementUnitCreateSchema().load(to_plain_dict(request.get_json(silent=True), "Request body is required")))
            item = CreateMeasurementUnitUseCase(SQLAlchemyMeasurementUnitRepository()).execute(CreateMeasurementUnitCommand(data["name"], required_uuid(_identity().get("user_id"), "Current user id is required")))
            return {"msg": "New measurement unit added successfully", "measurement_unit_id": str(item.measurement_unit_id)}, 200
        except Exception as error: return _error(error)


@measurement_unit_ns.route("/<string:measurement_unit_id>/view")
class MeasurementUnitView(Resource):
    @api_key_or_jwt_required
    @measurement_unit_ns.marshal_with(measurement_unit_response)
    def get(self, measurement_unit_id):
        try:
            item = GetMeasurementUnitUseCase(SQLAlchemyMeasurementUnitRepository()).execute(_id(measurement_unit_id))
            return {"msg": "Measurement unit found successfully", "measurement_unit": _response(item)}, 200
        except Exception as error: return _error(error)


@measurement_unit_ns.route("/<string:measurement_unit_id>/edit")
class MeasurementUnitEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @measurement_unit_ns.expect(measurement_unit_edit_model, validate=False)
    @measurement_unit_ns.marshal_with(measurement_unit_msg_model)
    def patch(self, measurement_unit_id):
        try:
            data = cast(_EditPayload, MeasurementUnitEditSchema().load(to_plain_dict(request.get_json(silent=True), "Request body is required")))
            item = UpdateMeasurementUnitUseCase(SQLAlchemyMeasurementUnitRepository()).execute(UpdateMeasurementUnitCommand(_id(measurement_unit_id), data["name"]))
            return {"msg": "Measurement unit edited successfully", "measurement_unit_id": str(item.measurement_unit_id)}, 200
        except Exception as error: return _error(error)


@measurement_unit_ns.route("/<string:measurement_unit_id>/delete/hard")
class MeasurementUnitDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @measurement_unit_ns.marshal_with(measurement_unit_msg_model)
    def delete(self, measurement_unit_id):
        try:
            DeleteMeasurementUnitUseCase(SQLAlchemyMeasurementUnitRepository()).execute(_id(measurement_unit_id))
            return {"msg": "Measurement unit deleted successfully", "measurement_unit_id": measurement_unit_id}, 200
        except Exception as error: return _error(error)


@measurement_unit_ns.route("/all")
class MeasurementUnitAll(Resource):
    @api_key_or_jwt_required
    @measurement_unit_ns.expect(measurement_unit_filter_parser)
    @measurement_unit_ns.marshal_with(measurement_unit_all_response)
    def get(self):
        try:
            data = cast(_FilterPayload, MeasurementUnitFilterSchema().load(to_plain_dict(request.args, "Request query is required")))
            items = ListMeasurementUnitsUseCase(SQLAlchemyMeasurementUnitRepository()).execute(MeasurementUnitListQuery(offset=data["offset"], limit=data["limit"], name=data.get("name")))
            return {"msg": "Measurement units found successfully", "measurement_units": [_response(item) for item in items]}, 200
        except Exception as error: return _error(error)
