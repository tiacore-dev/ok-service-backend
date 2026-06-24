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

from app.adapters.works import (
    SQLAlchemyWorkRepository,
    work_entity_to_response,
)
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.works import WorkNotFoundError, WorkValidationError
from app.routes.models.work_models import (
    work_all_response,
    work_create_model,
    work_edit_model,
    work_filter_parser,
    work_model,
    work_msg_model,
    work_response,
)
from app.schemas.work_schemas import WorkCreateSchema, WorkEditSchema, WorkFilterSchema
from app.use_cases.works import (
    CreateWorkCommand,
    CreateWorkUseCase,
    GetWorkUseCase,
    HardDeleteWorkUseCase,
    ListWorksUseCase,
    SoftDeleteWorkUseCase,
    UpdateWorkCommand,
    UpdateWorkUseCase,
    WorkListQuery,
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

work_ns = Namespace("works", description="Works management operations")

work_ns.models[work_create_model.name] = work_create_model
work_ns.models[work_edit_model.name] = work_edit_model
work_ns.models[work_msg_model.name] = work_msg_model
work_ns.models[work_response.name] = work_response
work_ns.models[work_all_response.name] = work_all_response
work_ns.models[work_model.name] = work_model


class WorkCreatePayload(TypedDict):
    name: str
    category: str | None
    measurement_unit: str | None


class WorkEditPayload(TypedDict, total=False):
    name: str
    category: str | None
    measurement_unit: str | None
    deleted: bool


class WorkFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    name: str
    deleted: bool
    sort_by: str
    sort_order: str


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


def _repository() -> SQLAlchemyWorkRepository:
    return SQLAlchemyWorkRepository()


def _parse_work_id(work_id: str) -> UUID:
    try:
        return UUID(work_id)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _map_error(error: Exception):
    if isinstance(error, WorkNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, WorkValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete work: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@work_ns.route("/add")
class WorkAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_ns.expect(work_create_model)
    @work_ns.marshal_with(work_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new work", extra={"login": current_user})
        schema = WorkCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(WorkCreatePayload, schema.load(raw_payload))
            work = CreateWorkUseCase(repository=_repository()).execute(
                CreateWorkCommand(
                    name=data["name"],
                    category=get_optional_uuid(data, "category"),
                    measurement_unit=get_optional_str(data, "measurement_unit"),
                    created_by=get_required_uuid(
                        current_user, "user_id", "Current user id is required"
                    ),
                )
            )
            return {
                "msg": "New work added successfully",
                "work_id": str(work.work_id),
            }, 200
        except Exception as error:
            logger.error(f"Error adding work: {error}", extra={"login": current_user})
            return _map_error(error)


@work_ns.route("/<string:work_id>/view")
class WorkView(Resource):
    @api_key_or_jwt_required
    @work_ns.marshal_with(work_response)
    def get(self, work_id):
        current_user = _get_current_user()
        logger.info(f"Request to view work: {work_id}", extra={"login": current_user})
        try:
            work = GetWorkUseCase(repository=_repository()).execute(
                _parse_work_id(work_id)
            )
            return {
                "msg": "Work found successfully",
                "work": work_entity_to_response(work),
            }, 200
        except Exception as error:
            logger.error(f"Error viewing work: {error}", extra={"login": current_user})
            return _map_error(error)


@work_ns.route("/<string:work_id>/delete/soft")
class WorkSoftDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_ns.marshal_with(work_msg_model)
    def patch(self, work_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to soft delete work: {work_id}", extra={"login": current_user}
        )
        try:
            SoftDeleteWorkUseCase(repository=_repository()).execute(
                _parse_work_id(work_id)
            )
            return {
                "msg": f"Work {work_id} soft deleted successfully",
                "work_id": work_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error soft deleting work: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@work_ns.route("/<string:work_id>/delete/hard")
class WorkHardDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_ns.marshal_with(work_msg_model)
    def delete(self, work_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete work: {work_id}", extra={"login": current_user}
        )
        try:
            HardDeleteWorkUseCase(repository=_repository()).execute(
                _parse_work_id(work_id)
            )
            return {
                "msg": f"Work {work_id} hard deleted successfully",
                "work_id": work_id,
            }, 200
        except IntegrityError:
            logger.warning(
                f"Cannot delete work due to dependencies: {work_id}",
                extra={"login": current_user},
            )
            return {"msg": "Cannot delete work: dependent data exists."}, 409
        except Exception as error:
            logger.error(
                f"Error hard deleting work: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@work_ns.route("/<string:work_id>/edit")
class WorkEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_ns.expect(work_edit_model)
    @work_ns.marshal_with(work_msg_model)
    def patch(self, work_id):
        current_user = _get_current_user()
        logger.info(f"Request to edit work: {work_id}", extra={"login": current_user})
        schema = WorkEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(WorkEditPayload, schema.load(raw_payload))
            work = UpdateWorkUseCase(repository=_repository()).execute(
                UpdateWorkCommand(
                    work_id=_parse_work_id(work_id),
                    name=get_optional_str(data, "name"),
                    category=get_optional_uuid(data, "category"),
                    measurement_unit=get_optional_str(data, "measurement_unit"),
                    deleted=get_optional_bool(data, "deleted"),
                )
            )
            return {
                "msg": "Work edited successfully",
                "work_id": str(work.work_id),
            }, 200
        except Exception as error:
            logger.error(f"Error editing work: {error}", extra={"login": current_user})
            return _map_error(error)


@work_ns.route("/all")
class WorkAll(Resource):
    @api_key_or_jwt_required
    @work_ns.expect(work_filter_parser)
    @work_ns.marshal_with(work_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all works", extra={"login": current_user})
        schema = WorkFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            args = cast(WorkFilterPayload, schema.load(raw_args))
            query = WorkListQuery(
                offset=get_optional_int(args, "offset") or 0,
                limit=get_optional_int(args, "limit"),
                sort_by=get_optional_str(args, "sort_by") or "created_at",
                sort_order=get_optional_str(args, "sort_order") or "asc",
                name=get_optional_str(args, "name"),
                deleted=get_optional_bool(args, "deleted"),
            )
            works = ListWorksUseCase(repository=_repository()).execute(query)
            return {
                "msg": "Works found successfully",
                "works": [work_entity_to_response(item) for item in works],
            }, 200
        except ValidationError as err:
            logger.error(
                f"Validation error while filtering works: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        except Exception as error:
            logger.error(
                f"Error fetching works: {error}", extra={"login": current_user}
            )
            return _map_error(error)
