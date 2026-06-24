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

from app.adapters.work_categories import (
    SQLAlchemyWorkCategoryRepository,
    work_category_entity_to_response,
)
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.work_categories import (
    WorkCategoryNotFoundError,
    WorkCategoryValidationError,
)
from app.routes.models.work_category_models import (
    work_category_all_response,
    work_category_create_model,
    work_category_edit_model,
    work_category_filter_parser,
    work_category_model,
    work_category_msg_model,
    work_category_response,
)
from app.schemas.work_category_schemas import (
    WorkCategoryCreateSchema,
    WorkCategoryEditSchema,
    WorkCategoryFilterSchema,
)
from app.use_cases.work_categories import (
    CreateWorkCategoryCommand,
    CreateWorkCategoryUseCase,
    DeleteWorkCategoryUseCase,
    GetWorkCategoryUseCase,
    ListWorkCategoriesUseCase,
    UpdateWorkCategoryCommand,
    UpdateWorkCategoryUseCase,
    WorkCategoryListQuery,
)
from app.web._typing import (
    get_optional_bool,
    get_optional_int,
    get_optional_str,
    required_uuid,
    to_plain_dict,
)

logger = logging.getLogger("ok_service")

work_category_ns = Namespace(
    "work_categories", description="Work category management operations"
)

work_category_ns.models[work_category_create_model.name] = work_category_create_model
work_category_ns.models[work_category_edit_model.name] = work_category_edit_model
work_category_ns.models[work_category_msg_model.name] = work_category_msg_model
work_category_ns.models[work_category_response.name] = work_category_response
work_category_ns.models[work_category_all_response.name] = work_category_all_response
work_category_ns.models[work_category_model.name] = work_category_model


class WorkCategoryCreatePayload(TypedDict):
    name: str


class WorkCategoryEditPayload(TypedDict, total=False):
    name: str
    deleted: bool


class WorkCategoryFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    name: str
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


def _repository() -> SQLAlchemyWorkCategoryRepository:
    return SQLAlchemyWorkCategoryRepository()


def _parse_work_category_id(work_category_id: str) -> UUID:
    try:
        return UUID(work_category_id)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _map_error(error: Exception):
    if isinstance(error, WorkCategoryNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, WorkCategoryValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete work category: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@work_category_ns.route("/add")
class WorkCategoryAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_category_ns.expect(work_category_create_model, validate=False)
    @work_category_ns.marshal_with(work_category_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new work category", extra={"login": current_user})

        schema = WorkCategoryCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(WorkCategoryCreatePayload, schema.load(raw_payload))
            work_category = CreateWorkCategoryUseCase(repository=_repository()).execute(
                CreateWorkCategoryCommand(
                    name=data["name"],
                    created_by=required_uuid(
                        current_user.get("user_id"), "Current user id is required"
                    ),
                )
            )
            return {
                "msg": "New work category added successfully",
                "work_category_id": str(work_category.work_category_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding work category: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@work_category_ns.route("/<string:work_category_id>/view")
class WorkCategoryView(Resource):
    @api_key_or_jwt_required
    @work_category_ns.marshal_with(work_category_response)
    def get(self, work_category_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view work category: {work_category_id}",
            extra={"login": current_user},
        )
        try:
            work_category = GetWorkCategoryUseCase(repository=_repository()).execute(
                _parse_work_category_id(work_category_id)
            )
            return {
                "msg": "Work category found successfully",
                "work_category": work_category_entity_to_response(work_category),
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing work category: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@work_category_ns.route("/<string:work_category_id>/delete/soft")
class WorkCategoryDeleteSoft(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_category_ns.marshal_with(work_category_msg_model)
    def patch(self, work_category_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to soft delete work category: {work_category_id}",
            extra={"login": current_user},
        )
        try:
            work_category = UpdateWorkCategoryUseCase(repository=_repository()).execute(
                UpdateWorkCategoryCommand(
                    work_category_id=_parse_work_category_id(work_category_id),
                    deleted=True,
                )
            )
            return {
                "msg": f"Work category {work_category.work_category_id} soft deleted successfully",
                "work_category_id": str(work_category.work_category_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error soft deleting work category: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@work_category_ns.route("/<string:work_category_id>/delete/hard")
class WorkCategoryDeleteHard(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_category_ns.marshal_with(work_category_msg_model)
    def delete(self, work_category_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete work category: {work_category_id}",
            extra={"login": current_user},
        )
        try:
            deleted = DeleteWorkCategoryUseCase(repository=_repository()).execute(
                _parse_work_category_id(work_category_id)
            )
            if not deleted:
                raise WorkCategoryNotFoundError("Work category not found")
            return {
                "msg": f"Work category {work_category_id} hard deleted successfully",
                "work_category_id": work_category_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting work category: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@work_category_ns.route("/<string:work_category_id>/edit")
class WorkCategoryEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_category_ns.expect(work_category_edit_model, validate=False)
    @work_category_ns.marshal_with(work_category_msg_model)
    def patch(self, work_category_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit work category: {work_category_id}",
            extra={"login": current_user},
        )
        schema = WorkCategoryEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(WorkCategoryEditPayload, schema.load(raw_payload))
            if not data.get("name"):
                return {"msg": "Bad request, invalid data."}, 400
            work_category = UpdateWorkCategoryUseCase(repository=_repository()).execute(
                UpdateWorkCategoryCommand(
                    work_category_id=_parse_work_category_id(work_category_id),
                    name=get_optional_str(data, "name"),
                    deleted=get_optional_bool(data, "deleted"),
                )
            )
            return {
                "msg": "Work category edited successfully",
                "work_category_id": str(work_category.work_category_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing work category: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@work_category_ns.route("/all")
class WorkCategoryAll(Resource):
    @api_key_or_jwt_required
    @work_category_ns.expect(work_category_filter_parser)
    @work_category_ns.marshal_with(work_category_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all work categories", extra={"login": current_user})

        schema = WorkCategoryFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            args = cast(WorkCategoryFilterPayload, schema.load(raw_args))
            query = WorkCategoryListQuery(
                offset=get_optional_int(args, "offset") or 0,
                limit=get_optional_int(args, "limit"),
                sort_by=get_optional_str(args, "sort_by") or "created_at",
                sort_order=get_optional_str(args, "sort_order") or "desc",
                name=get_optional_str(args, "name"),
                deleted=get_optional_bool(args, "deleted"),
            )
            work_categories = ListWorkCategoriesUseCase(repository=_repository()).execute(
                query
            )
            return {
                "msg": "Work categories found successfully",
                "work_categories": [
                    work_category_entity_to_response(item) for item in work_categories
                ],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching work categories: {error}", extra={"login": current_user}
            )
            return _map_error(error)
