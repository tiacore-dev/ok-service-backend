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

from app.adapters.project_schedules import (
    SQLAlchemyProjectScheduleRepository,
    project_schedule_entity_to_response,
)
from app.decorators import api_key_or_jwt_required, user_forbidden
from app.domain.project_schedules import (
    ProjectScheduleForbiddenError,
    ProjectScheduleNotFoundError,
)
from app.schemas.project_schedule_schemas import (
    ProjectScheduleCreateSchema,
    ProjectScheduleEditSchema,
    ProjectScheduleFilterSchema,
)
from app.use_cases.project_schedules import (
    CreateProjectScheduleCommand,
    CreateProjectScheduleUseCase,
    GetProjectScheduleUseCase,
    HardDeleteProjectScheduleUseCase,
    ListProjectSchedulesUseCase,
    ProjectScheduleActor,
    ProjectScheduleListQuery,
    UpdateProjectScheduleCommand,
    UpdateProjectScheduleUseCase,
)
from app.web._typing import (
    get_optional_float,
    get_optional_int,
    get_optional_uuid,
    get_required_float,
    get_required_uuid,
    to_plain_dict,
)

from .models import (
    project_schedule_all_response,
    project_schedule_create_model,
    project_schedule_edit_model,
    project_schedule_filter_parser,
    project_schedule_model,
    project_schedule_msg_model,
    project_schedule_response,
)

logger = logging.getLogger("ok_service")

project_schedule_ns = Namespace(
    "project_schedules", description="Project schedules management operations"
)

project_schedule_ns.models[project_schedule_create_model.name] = (
    project_schedule_create_model
)
project_schedule_ns.models[project_schedule_edit_model.name] = project_schedule_edit_model
project_schedule_ns.models[project_schedule_msg_model.name] = project_schedule_msg_model
project_schedule_ns.models[project_schedule_response.name] = project_schedule_response
project_schedule_ns.models[project_schedule_all_response.name] = (
    project_schedule_all_response
)
project_schedule_ns.models[project_schedule_model.name] = project_schedule_model


class ProjectScheduleCreatePayload(TypedDict):
    work: str
    project: str
    quantity: float
    date: int | None


class ProjectScheduleEditPayload(TypedDict, total=False):
    work: str | None
    project: str | None
    quantity: float | None
    date: int | None


class ProjectScheduleFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    work: str
    project: str
    date: int


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


def _repository() -> SQLAlchemyProjectScheduleRepository:
    return SQLAlchemyProjectScheduleRepository()


def _parse_schedule_id(schedule_id: str) -> UUID:
    return get_required_uuid({"schedule_id": schedule_id}, "schedule_id", "Invalid UUID format")


def _actor(current_user: dict[str, Any]) -> ProjectScheduleActor:
    return ProjectScheduleActor(
        role=str(current_user.get("role", "")),
        user_id=get_required_uuid(current_user, "user_id", "Current user id is required"),
    )


def _map_error(error: Exception):
    if isinstance(error, ProjectScheduleNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, ProjectScheduleForbiddenError):
        return {"msg": str(error)}, 403
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete project schedule: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@project_schedule_ns.route("/add")
class ProjectScheduleAdd(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_schedule_ns.expect(project_schedule_create_model)
    @project_schedule_ns.marshal_with(project_schedule_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info(
            "Request to add new project schedule", extra={"login": current_user}
        )
        schema = ProjectScheduleCreateSchema()
        try:
            raw_payload = to_plain_dict(request.get_json(silent=True), "Request body is required")
            data = cast(ProjectScheduleCreatePayload, schema.load(raw_payload))
            schedule = CreateProjectScheduleUseCase(repository=_repository()).execute(
                CreateProjectScheduleCommand(
                    project=get_required_uuid(data, "project", "Project is required"),
                    work=get_required_uuid(data, "work", "Work is required"),
                    quantity=get_required_float(data, "quantity", "Quantity is required"),
                    date=get_optional_int(data, "date"),
                    created_by=get_required_uuid(
                        current_user, "user_id", "Current user id is required"
                    ),
                ),
                _actor(current_user),
            )
            return {
                "msg": "New project schedule added successfully",
                "project_schedule_id": str(schedule.project_schedule_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding project schedule: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_schedule_ns.route("/<string:schedule_id>/view")
class ProjectScheduleView(Resource):
    @api_key_or_jwt_required
    @project_schedule_ns.marshal_with(project_schedule_response)
    def get(self, schedule_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view project schedule: {schedule_id}",
            extra={"login": current_user},
        )
        try:
            schedule = GetProjectScheduleUseCase(repository=_repository()).execute(
                _parse_schedule_id(schedule_id)
            )
            return {
                "msg": "Project schedule found successfully",
                "project_schedule": project_schedule_entity_to_response(schedule),
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing project schedule: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_schedule_ns.route("/<string:schedule_id>/delete/hard")
class ProjectScheduleHardDelete(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_schedule_ns.marshal_with(project_schedule_msg_model)
    def delete(self, schedule_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete project schedule: {schedule_id}",
            extra={"login": current_user},
        )
        try:
            HardDeleteProjectScheduleUseCase(repository=_repository()).execute(
                _parse_schedule_id(schedule_id),
                _actor(current_user),
            )
            return {
                "msg": f"Project schedule {schedule_id} hard deleted successfully",
                "project_schedule_id": schedule_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting project schedule: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@project_schedule_ns.route("/<string:schedule_id>/edit")
class ProjectScheduleEdit(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_schedule_ns.expect(project_schedule_edit_model)
    @project_schedule_ns.marshal_with(project_schedule_msg_model)
    def patch(self, schedule_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit project schedule: {schedule_id}",
            extra={"login": current_user},
        )
        schema = ProjectScheduleEditSchema()
        try:
            raw_payload = to_plain_dict(request.get_json(silent=True), "Request body is required")
            data = cast(ProjectScheduleEditPayload, schema.load(raw_payload))
            if not any(value is not None for value in data.values()):
                raise ValueError("No data provided for update")
            schedule = UpdateProjectScheduleUseCase(repository=_repository()).execute(
                UpdateProjectScheduleCommand(
                    project_schedule_id=_parse_schedule_id(schedule_id),
                    project=get_optional_uuid(data, "project"),
                    work=get_optional_uuid(data, "work"),
                    quantity=get_optional_float(data, "quantity"),
                    date=get_optional_int(data, "date"),
                ),
                _actor(current_user),
            )
            return {
                "msg": "Project schedule updated successfully",
                "project_schedule_id": str(schedule.project_schedule_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing project schedule: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_schedule_ns.route("/all")
class ProjectScheduleAll(Resource):
    @api_key_or_jwt_required
    @project_schedule_ns.expect(project_schedule_filter_parser)
    @project_schedule_ns.marshal_with(project_schedule_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info(
            "Request to fetch all project schedules", extra={"login": current_user}
        )
        schema = ProjectScheduleFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            data = cast(ProjectScheduleFilterPayload, schema.load(raw_args))
            schedules = ListProjectSchedulesUseCase(repository=_repository()).execute(
                ProjectScheduleListQuery(
                    offset=data.get("offset", 0),
                    limit=data.get("limit", 10),
                    sort_by=data.get("sort_by"),
                    sort_order=data.get("sort_order", "desc"),
                    work=get_optional_uuid(data, "work"),
                    project=get_optional_uuid(data, "project"),
                    date=get_optional_int(data, "date"),
                )
            )
            return {
                "msg": "Project schedules found successfully",
                "project_schedules": [
                    project_schedule_entity_to_response(item) for item in schedules
                ],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching project schedules: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)
