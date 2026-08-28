from __future__ import annotations

from typing import Any, TypedDict, cast
from uuid import UUID

from flask import request
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.work_acceptance_relations import SQLAlchemyWorkAcceptanceRelationRepository
from app.decorators import admin_or_manager_required, api_key_or_jwt_required
from app.domain.work_acceptance_relations import WorkAcceptanceRelationNotFoundError, WorkAcceptanceRelationValidationError
from app.routes.models.work_acceptance_relation_models import work_acceptance_relation_all_response, work_acceptance_relation_create_model, work_acceptance_relation_edit_model, work_acceptance_relation_filter_parser, work_acceptance_relation_model, work_acceptance_relation_msg_model, work_acceptance_relation_response
from app.schemas.work_acceptance_relation_schemas import WorkAcceptanceRelationCreateSchema, WorkAcceptanceRelationEditSchema, WorkAcceptanceRelationFilterSchema
from app.use_cases.work_acceptance_relations import CreateWorkAcceptanceRelationCommand, CreateWorkAcceptanceRelationUseCase, DeleteWorkAcceptanceRelationUseCase, GetWorkAcceptanceRelationUseCase, ListWorkAcceptanceRelationsUseCase, UpdateWorkAcceptanceRelationCommand, UpdateWorkAcceptanceRelationUseCase, WorkAcceptanceRelationListQuery
from app.web._typing import get_optional_decimal, get_required_decimal, get_required_uuid, optional_uuid

work_acceptance_relation_ns = Namespace(
    "work_acceptance_relations",
    description="Work acceptance relations management operations",
    path="/work-acceptance-relations",
)
for model in (work_acceptance_relation_create_model, work_acceptance_relation_edit_model, work_acceptance_relation_model, work_acceptance_relation_msg_model, work_acceptance_relation_response, work_acceptance_relation_all_response):
    work_acceptance_relation_ns.models[model.name] = model


class RelationCreatePayload(TypedDict):
    acceptance_id: str
    work_id: str
    quantity: Any


class RelationEditPayload(TypedDict, total=False):
    acceptance_id: str | None
    work_id: str | None
    quantity: Any


class RelationFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    acceptance_id: str
    work_id: str


def _id(value: str) -> UUID:
    return get_required_uuid({"id": value}, "id", "Invalid UUID format")


def _json_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("Request body is required")
    return cast(dict[str, Any], payload)


def _response(item):
    return {"id": str(item.id), "acceptance_id": str(item.acceptance_id), "work_id": str(item.work_id), "quantity": float(item.quantity)}


def _error(error: Exception):
    if isinstance(error, WorkAcceptanceRelationNotFoundError): return {"msg": str(error)}, 404
    if isinstance(error, (WorkAcceptanceRelationValidationError, ValidationError, ValueError)): return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError): return {"msg": "Cannot delete work acceptance relation: dependent data exists."}, 409
    return {"msg": f"Internal error: {error}"}, 500


@work_acceptance_relation_ns.route("/add")
class RelationAdd(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @work_acceptance_relation_ns.expect(work_acceptance_relation_create_model, validate=False)
    @work_acceptance_relation_ns.marshal_with(work_acceptance_relation_msg_model)
    def post(self):
        try:
            data = cast(RelationCreatePayload, WorkAcceptanceRelationCreateSchema().load(_json_payload()))
            item = CreateWorkAcceptanceRelationUseCase(SQLAlchemyWorkAcceptanceRelationRepository()).execute(CreateWorkAcceptanceRelationCommand(
                acceptance_id=get_required_uuid(data, "acceptance_id", "Acceptance id is required"),
                work_id=get_required_uuid(data, "work_id", "Work id is required"),
                quantity=get_required_decimal(data, "quantity", "Quantity is required")))
            return {"msg": "Work acceptance relation added successfully", "id": str(item.id)}, 200
        except Exception as error: return _error(error)


@work_acceptance_relation_ns.route("/<string:relation_id>/view")
class RelationView(Resource):
    @api_key_or_jwt_required
    @work_acceptance_relation_ns.marshal_with(work_acceptance_relation_response)
    def get(self, relation_id):
        try: return {"msg": "Work acceptance relation found successfully", "work_acceptance_relation": _response(GetWorkAcceptanceRelationUseCase(SQLAlchemyWorkAcceptanceRelationRepository()).execute(_id(relation_id)))}, 200
        except Exception as error: return _error(error)


@work_acceptance_relation_ns.route("/<string:relation_id>/edit")
class RelationEdit(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @work_acceptance_relation_ns.expect(work_acceptance_relation_edit_model, validate=False)
    @work_acceptance_relation_ns.marshal_with(work_acceptance_relation_msg_model)
    def patch(self, relation_id):
        try:
            data = cast(RelationEditPayload, WorkAcceptanceRelationEditSchema().load(_json_payload()))
            item = UpdateWorkAcceptanceRelationUseCase(SQLAlchemyWorkAcceptanceRelationRepository()).execute(UpdateWorkAcceptanceRelationCommand(
                id=_id(relation_id), acceptance_id=optional_uuid(data.get("acceptance_id")), work_id=optional_uuid(data.get("work_id")), quantity=get_optional_decimal(data, "quantity")))
            return {"msg": "Work acceptance relation edited successfully", "id": str(item.id)}, 200
        except Exception as error: return _error(error)


@work_acceptance_relation_ns.route("/<string:relation_id>/delete/hard")
class RelationDelete(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @work_acceptance_relation_ns.marshal_with(work_acceptance_relation_msg_model)
    def delete(self, relation_id):
        try:
            deleted = DeleteWorkAcceptanceRelationUseCase(SQLAlchemyWorkAcceptanceRelationRepository()).execute(_id(relation_id))
            if not deleted: raise WorkAcceptanceRelationNotFoundError("Work acceptance relation not found")
            return {"msg": "Work acceptance relation deleted successfully", "id": relation_id}, 200
        except Exception as error: return _error(error)


@work_acceptance_relation_ns.route("/all")
class RelationAll(Resource):
    @api_key_or_jwt_required
    @work_acceptance_relation_ns.expect(work_acceptance_relation_filter_parser)
    @work_acceptance_relation_ns.marshal_with(work_acceptance_relation_all_response)
    def get(self):
        try:
            data = cast(RelationFilterPayload, WorkAcceptanceRelationFilterSchema().load(request.args.to_dict()))
            items = ListWorkAcceptanceRelationsUseCase(SQLAlchemyWorkAcceptanceRelationRepository()).execute(WorkAcceptanceRelationListQuery(
                offset=data.get("offset", 0), limit=data.get("limit", 1000), acceptance_id=optional_uuid(data.get("acceptance_id")), work_id=optional_uuid(data.get("work_id"))))
            return {"msg": "Work acceptance relations found successfully", "work_acceptance_relations": [_response(item) for item in items]}, 200
        except Exception as error: return _error(error)
