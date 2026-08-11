from __future__ import annotations

import json
from typing import Any, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.place_relations import SQLAlchemyPlaceRelationRepository
from app.decorators import api_key_or_jwt_required, user_forbidden
from app.use_cases.place_relations import (
    PlaceRelationConflictError, PlaceRelationForbiddenError, PlaceRelationNotFoundError,
    PlaceRelationService, RelationActor,
)
from app.web._typing import to_plain_dict
from app.schemas.place_relation_schemas import (
    ProjectPlaceRelationCreateSchema, ProjectPlaceRelationEditSchema,
    ShiftPlaceRelationCreateSchema, ShiftPlaceRelationEditSchema,
)
from app.routes.models.place_relation_models import *  # noqa: F403

project_place_relation_ns = Namespace("project_place_relations", description="Project-place relations")
shift_place_relation_ns = Namespace("shift_place_relations", description="Shift-place relations")
for _ns in (project_place_relation_ns, shift_place_relation_ns):
    for _model in (project_place_relation_create_model, project_place_relation_edit_model, shift_place_relation_create_model, shift_place_relation_edit_model, project_place_relation_model, shift_place_relation_model, project_place_relation_msg_model, shift_place_relation_msg_model, project_place_relation_response, shift_place_relation_response, project_place_relation_all_response, shift_place_relation_all_response):
        _ns.models[_model.name] = _model


def _identity() -> dict[str, Any]:
    value = getattr(g, "api_key_identity_json", None) if getattr(g, "auth_via_api_key", False) else _get_jwt_identity()
    if isinstance(value, dict): return value
    if isinstance(value, (str, bytes, bytearray)):
        try: value = json.loads(value)
        except (TypeError, ValueError): return {}
    return value if isinstance(value, dict) else {}


def _actor() -> RelationActor:
    return RelationActor(str(_identity().get("role", "")), UUID(str(_identity().get("user_id"))))


def _id(value: str) -> UUID:
    try: return UUID(value)
    except ValueError as error: raise ValueError("Invalid UUID format") from error


def _service() -> PlaceRelationService:
    return PlaceRelationService(SQLAlchemyPlaceRelationRepository())


def _error(error: Exception):
    if isinstance(error, PlaceRelationNotFoundError): return {"msg": str(error)}, 404
    if isinstance(error, PlaceRelationForbiddenError): return {"msg": str(error)}, 403
    if isinstance(error, PlaceRelationConflictError): return {"msg": str(error)}, 409
    if isinstance(error, IntegrityError): return {"msg": "Relation conflicts with dependent data."}, 409
    if isinstance(error, ValidationError): return {"error": error.messages}, 400
    if isinstance(error, ValueError): return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


def _project_response(item):
    return {"project_place_relation_id": str(item.project_place_relation_id), "project_id": str(item.project_id), "place_id": str(item.place_id)}


def _shift_response(item):
    return {"shift_place_relation_id": str(item.shift_place_relation_id), "shift_report_id": str(item.shift_report_id), "place_id": str(item.place_id), "comment": item.comment}


@project_place_relation_ns.route("/add")
class ProjectPlaceRelationAdd(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_place_relation_ns.expect(project_place_relation_create_model)
    @project_place_relation_ns.marshal_with(project_place_relation_msg_model)
    def post(self):
        try:
            data = cast(dict[str, Any], ProjectPlaceRelationCreateSchema().load(to_plain_dict(request.get_json(silent=True), "Request body is required")))
            item = _service().create_project_place(data["project_id"], data["place_id"], _actor())
            return {"msg": "Project place relation added successfully", "project_place_relation_id": str(item.project_place_relation_id)}, 200
        except Exception as error: return _error(error)


@project_place_relation_ns.route("/<string:relation_id>/view")
class ProjectPlaceRelationView(Resource):
    @api_key_or_jwt_required
    @project_place_relation_ns.marshal_with(project_place_relation_response)
    def get(self, relation_id):
        try:
            item = SQLAlchemyPlaceRelationRepository().get_project_place_relation(_id(relation_id))
            if item is None: raise PlaceRelationNotFoundError("Project place relation not found")
            return {"msg": "Project place relation found successfully", "project_place_relation": _project_response(item)}, 200
        except Exception as error: return _error(error)


@project_place_relation_ns.route("/all")
class ProjectPlaceRelationAll(Resource):
    @api_key_or_jwt_required
    @project_place_relation_ns.marshal_with(project_place_relation_all_response)
    def get(self):
        items = SQLAlchemyPlaceRelationRepository().list_project_place_relations()
        return {"msg": "Project place relations found successfully", "project_place_relations": [_project_response(item) for item in items]}, 200


@project_place_relation_ns.route("/<string:relation_id>/edit")
class ProjectPlaceRelationEdit(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_place_relation_ns.expect(project_place_relation_edit_model)
    @project_place_relation_ns.marshal_with(project_place_relation_msg_model)
    def patch(self, relation_id):
        try:
            data = cast(dict[str, Any], ProjectPlaceRelationEditSchema().load(to_plain_dict(request.get_json(silent=True), "Request body is required")))
            item = _service().update_project_place(_id(relation_id), data["project_id"], data["place_id"], _actor())
            return {"msg": "Project place relation edited successfully", "project_place_relation_id": str(item.project_place_relation_id)}, 200
        except Exception as error: return _error(error)


@project_place_relation_ns.route("/<string:relation_id>/delete/hard")
class ProjectPlaceRelationDelete(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_place_relation_ns.marshal_with(project_place_relation_msg_model)
    def delete(self, relation_id):
        try:
            _service().delete_project_place(_id(relation_id), _actor())
            return {"msg": "Project place relation deleted successfully", "project_place_relation_id": relation_id}, 200
        except Exception as error: return _error(error)


@shift_place_relation_ns.route("/add")
class ShiftPlaceRelationAdd(Resource):
    @api_key_or_jwt_required
    @shift_place_relation_ns.expect(shift_place_relation_create_model)
    @shift_place_relation_ns.marshal_with(shift_place_relation_msg_model)
    def post(self):
        try:
            data = cast(dict[str, Any], ShiftPlaceRelationCreateSchema().load(to_plain_dict(request.get_json(silent=True), "Request body is required")))
            item = _service().create_shift_place(data["shift_report_id"], data["place_id"], data.get("comment"), _actor())
            return {"msg": "Shift place relation added successfully", "shift_place_relation_id": str(item.shift_place_relation_id)}, 200
        except Exception as error: return _error(error)


@shift_place_relation_ns.route("/<string:relation_id>/view")
class ShiftPlaceRelationView(Resource):
    @api_key_or_jwt_required
    @shift_place_relation_ns.marshal_with(shift_place_relation_response)
    def get(self, relation_id):
        try:
            item = SQLAlchemyPlaceRelationRepository().get_shift_place_relation(_id(relation_id))
            if item is None: raise PlaceRelationNotFoundError("Shift place relation not found")
            return {"msg": "Shift place relation found successfully", "shift_place_relation": _shift_response(item)}, 200
        except Exception as error: return _error(error)


@shift_place_relation_ns.route("/all")
class ShiftPlaceRelationAll(Resource):
    @api_key_or_jwt_required
    @shift_place_relation_ns.marshal_with(shift_place_relation_all_response)
    def get(self):
        items = SQLAlchemyPlaceRelationRepository().list_shift_place_relations()
        return {"msg": "Shift place relations found successfully", "shift_place_relations": [_shift_response(item) for item in items]}, 200


@shift_place_relation_ns.route("/<string:relation_id>/edit")
class ShiftPlaceRelationEdit(Resource):
    @api_key_or_jwt_required
    @shift_place_relation_ns.expect(shift_place_relation_edit_model)
    @shift_place_relation_ns.marshal_with(shift_place_relation_msg_model)
    def patch(self, relation_id):
        try:
            data = cast(dict[str, Any], ShiftPlaceRelationEditSchema().load(to_plain_dict(request.get_json(silent=True), "Request body is required")))
            current = SQLAlchemyPlaceRelationRepository().get_shift_place_relation(_id(relation_id))
            if current is None: raise PlaceRelationNotFoundError("Shift place relation not found")
            item = _service().update_shift_place(_id(relation_id), data.get("place_id", current.place_id), data.get("comment", current.comment), _actor())
            return {"msg": "Shift place relation edited successfully", "shift_place_relation_id": str(item.shift_place_relation_id)}, 200
        except Exception as error: return _error(error)


@shift_place_relation_ns.route("/<string:relation_id>/delete/hard")
class ShiftPlaceRelationDelete(Resource):
    @api_key_or_jwt_required
    @shift_place_relation_ns.marshal_with(shift_place_relation_msg_model)
    def delete(self, relation_id):
        try:
            _service().delete_shift_place(_id(relation_id), _actor())
            return {"msg": "Shift place relation deleted successfully", "shift_place_relation_id": relation_id}, 200
        except Exception as error: return _error(error)
