from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any, NotRequired, TypedDict, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.project_works import (
    SQLAlchemyProjectWorkRepository,
    project_work_entity_to_response,
)
from app.decorators import api_key_or_jwt_required, user_forbidden
from app.domain.project_works import (
    ProjectWorkForbiddenError,
    ProjectWorkNotFoundError,
    ProjectWorkValidationError,
)
from app.routes.models.project_work_models import (
    project_work_all_response,
    project_work_create_model,
    project_work_edit_model,
    project_work_filter_parser,
    project_work_model,
    project_work_msg_many_model,
    project_work_msg_model,
    project_work_response,
)
from app.schemas.project_work_schemas import (
    ProjectWorkCreateSchema,
    ProjectWorkEditSchema,
    ProjectWorkFilterSchema,
)
from app.use_cases.project_works import (
    BulkCreateProjectWorksCommand,
    BulkCreateProjectWorksUseCase,
    CreateProjectWorkCommand,
    CreateProjectWorkUseCase,
    DeleteProjectWorkUseCase,
    GetProjectWorkUseCase,
    ListProjectWorksUseCase,
    ProjectWorkActor,
    ProjectWorkListQuery,
    SoftDeleteProjectWorkUseCase,
    UpdateProjectWorkCommand,
    UpdateProjectWorkUseCase,
)
from app.web._typing import (
    get_optional_bool,
    get_optional_decimal,
    get_optional_float,
    get_optional_int,
    get_optional_str,
    get_optional_uuid,
    get_required_decimal,
    get_required_uuid,
    to_plain_dict,
)

logger = logging.getLogger("ok_service")

project_work_ns = Namespace("project_works", description="Project Works management operations")

project_work_ns.models[project_work_create_model.name] = project_work_create_model
project_work_ns.models[project_work_edit_model.name] = project_work_edit_model
project_work_ns.models[project_work_msg_model.name] = project_work_msg_model
project_work_ns.models[project_work_msg_many_model.name] = project_work_msg_many_model
project_work_ns.models[project_work_response.name] = project_work_response
project_work_ns.models[project_work_all_response.name] = project_work_all_response
project_work_ns.models[project_work_model.name] = project_work_model


class ProjectWorkCreatePayload(TypedDict):
    project: str
    project_work_name: str
    work: str
    quantity: float | int
    summ: NotRequired[float | int | None]
    signed: NotRequired[bool]


class ProjectWorkEditPayload(TypedDict, total=False):
    project: str
    project_work_name: str
    work: str
    quantity: float | int
    summ: float | int | None
    signed: bool


class ProjectWorkFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    signed: bool
    work: str
    project: str
    project_work_name: str
    min_quantity: float | int
    max_quantity: float | int
    min_summ: float | int
    max_summ: float | int


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


def _repository() -> SQLAlchemyProjectWorkRepository:
    return SQLAlchemyProjectWorkRepository()


def _parse_project_work_id(project_work_id: str) -> UUID:
    try:
        return UUID(project_work_id)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _actor(current_user: dict[str, Any]) -> ProjectWorkActor:
    return ProjectWorkActor(
        role=str(current_user.get("role") or ""),
        user_id=get_required_uuid(current_user, "user_id", "Current user id is required"),
    )


def _map_error(error: Exception):
    if isinstance(error, ProjectWorkNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, ProjectWorkForbiddenError):
        return {"msg": str(error)}, 403
    if isinstance(error, ProjectWorkValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete project work: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@project_work_ns.route("/add/many")
class ProjectWorkAddBulk(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_work_ns.expect([project_work_create_model])
    @project_work_ns.marshal_with(project_work_msg_many_model)
    def post(self):
        current_user = _get_current_user()
        logger.info(
            "Request to add multiple project works", extra={"login": current_user}
        )

        schema = ProjectWorkCreateSchema(many=True)
        try:
            raw_payload = request.get_json(silent=True)
            if not isinstance(raw_payload, list):
                raise ValueError("Request body is required")
            data_list = cast(list[ProjectWorkCreatePayload], schema.load(raw_payload))
            commands = [
                CreateProjectWorkCommand(
                    project=get_required_uuid(item, "project", "Project is required"),
                    project_work_name=get_optional_str(item, "project_work_name"),
                    work=get_required_uuid(item, "work", "Work is required"),
                    quantity=get_required_decimal(
                        item, "quantity", "Quantity is required"
                    ),
                    summ=get_optional_decimal(item, "summ"),
                    signed=get_optional_bool(item, "signed"),
                    created_by=get_optional_uuid(current_user, "user_id"),
                )
                for item in data_list
            ]
            created = BulkCreateProjectWorksUseCase(repository=_repository()).execute(
                BulkCreateProjectWorksCommand(project_works=commands),
                _actor(current_user),
            )
            return {
                "msg": "Project works added successfully",
                "project_work_ids": [str(item.project_work_id) for item in created],
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding project works: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_work_ns.route("/add")
class ProjectWorkAdd(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_work_ns.expect(project_work_create_model)
    @project_work_ns.marshal_with(project_work_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new project work", extra={"login": current_user})

        schema = ProjectWorkCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ProjectWorkCreatePayload, schema.load(raw_payload))
            command = CreateProjectWorkCommand(
                project=get_required_uuid(data, "project", "Project is required"),
                project_work_name=get_optional_str(data, "project_work_name"),
                work=get_required_uuid(data, "work", "Work is required"),
                quantity=get_required_decimal(data, "quantity", "Quantity is required"),
                summ=get_optional_decimal(data, "summ"),
                signed=get_optional_bool(data, "signed"),
                created_by=get_optional_uuid(current_user, "user_id"),
            )
            project_work = CreateProjectWorkUseCase(repository=_repository()).execute(
                command,
                _actor(current_user),
            )
            return {
                "msg": "Project work added successfully",
                "project_work_id": str(project_work.project_work_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding project work: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_work_ns.route("/<string:project_work_id>/view")
class ProjectWorkView(Resource):
    @api_key_or_jwt_required
    @project_work_ns.marshal_with(project_work_response)
    def get(self, project_work_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view project work: {project_work_id}",
            extra={"login": current_user},
        )
        try:
            project_work = GetProjectWorkUseCase(repository=_repository()).execute(
                _parse_project_work_id(project_work_id)
            )
            return {
                "msg": "Project work found successfully",
                "project_work": project_work_entity_to_response(project_work),
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing project work: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_work_ns.route("/<string:project_work_id>/delete/soft")
class ProjectWorkSoftDelete(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_work_ns.marshal_with(project_work_msg_model)
    def patch(self, project_work_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to soft delete project work: {project_work_id}",
            extra={"login": current_user},
        )
        try:
            project_work = SoftDeleteProjectWorkUseCase(repository=_repository()).execute(
                _parse_project_work_id(project_work_id),
                _actor(current_user),
            )
            return {
                "msg": f"Project work {project_work.project_work_id} soft deleted successfully",
                "project_work_id": str(project_work.project_work_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error soft deleting project work: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@project_work_ns.route("/<string:project_work_id>/delete/hard")
class ProjectWorkHardDelete(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_work_ns.marshal_with(project_work_msg_model)
    def delete(self, project_work_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete project work: {project_work_id}",
            extra={"login": current_user},
        )
        try:
            deleted = DeleteProjectWorkUseCase(repository=_repository()).execute(
                _parse_project_work_id(project_work_id),
                _actor(current_user),
            )
            if not deleted:
                raise ProjectWorkNotFoundError("Project work not found")
            return {
                "msg": f"Project work {project_work_id} hard deleted successfully",
                "project_work_id": project_work_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting project work: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@project_work_ns.route("/<string:project_work_id>/edit")
class ProjectWorkEdit(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_work_ns.expect(project_work_edit_model, validate=False)
    @project_work_ns.marshal_with(project_work_msg_model)
    def patch(self, project_work_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit project work: {project_work_id}",
            extra={"login": current_user},
        )

        schema = ProjectWorkEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ProjectWorkEditPayload, schema.load(raw_payload))
            project_work = UpdateProjectWorkUseCase(repository=_repository()).execute(
                UpdateProjectWorkCommand(
                    project_work_id=_parse_project_work_id(project_work_id),
                    project=get_optional_uuid(data, "project"),
                    project_work_name=get_optional_str(data, "project_work_name"),
                    work=get_optional_uuid(data, "work"),
                    quantity=get_optional_decimal(data, "quantity"),
                    summ=get_optional_decimal(data, "summ"),
                    signed=get_optional_bool(data, "signed"),
                ),
                _actor(current_user),
            )
            return {
                "msg": "Project work edited successfully",
                "project_work_id": str(project_work.project_work_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing project work: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_work_ns.route("/all")
class ProjectWorkAll(Resource):
    @api_key_or_jwt_required
    @project_work_ns.expect(project_work_filter_parser)
    @project_work_ns.marshal_with(project_work_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all project works", extra={"login": current_user})

        schema = ProjectWorkFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            args = cast(ProjectWorkFilterPayload, schema.load(raw_args))
            query = ProjectWorkListQuery(
                offset=get_optional_int(args, "offset") or 0,
                limit=get_optional_int(args, "limit"),
                sort_by=get_optional_str(args, "sort_by") or "created_at",
                sort_order=get_optional_str(args, "sort_order") or "desc",
                signed=get_optional_bool(args, "signed"),
                work=get_optional_uuid(args, "work"),
                project=get_optional_uuid(args, "project"),
                project_work_name=get_optional_str(args, "project_work_name"),
                min_quantity=get_optional_decimal(args, "min_quantity"),
                max_quantity=get_optional_decimal(args, "max_quantity"),
                min_summ=get_optional_decimal(args, "min_summ"),
                max_summ=get_optional_decimal(args, "max_summ"),
            )
            project_works = ListProjectWorksUseCase(repository=_repository()).execute(
                query
            )
            return {
                "msg": "Project works found successfully",
                "project_works": [
                    project_work_entity_to_response(item) for item in project_works
                ],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching project works: {error}", extra={"login": current_user}
            )
            return _map_error(error)
