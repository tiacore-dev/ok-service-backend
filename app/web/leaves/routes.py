from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any, TypedDict, cast
from uuid import UUID

from flask import current_app, g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.leaves import (
    SQLAlchemyLeaveRepository,
    leave_entity_to_list_item,
    leave_entity_to_response,
)
from app.adapters.statistics import RedisProjectWorkStatistics
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.leaves import AbsenceReason, LeaveConflictError, LeaveNotFoundError
from app.routes.models.leave_models import (
    leave_all_response,
    leave_create_model,
    leave_edit_model,
    leave_filter_parser,
    leave_model,
    leave_msg_model,
    leave_reason_all_response,
    leave_reason_model,
    leave_response,
)
from app.schemas.leave_schemas import (
    LeaveCreateSchema,
    LeaveEditSchema,
    LeaveFilterSchema,
)
from app.use_cases.leaves import (
    CreateLeaveCommand,
    CreateLeaveUseCase,
    GetLeaveUseCase,
    HardDeleteLeaveUseCase,
    LeaveListQuery,
    ListAbsenceReasonsUseCase,
    ListLeavesUseCase,
    SoftDeleteLeaveUseCase,
    UpdateLeaveCommand,
    UpdateLeaveUseCase,
)
from app.web._typing import (
    get_optional_bool,
    get_optional_int,
    get_optional_str,
    optional_uuid,
    required_uuid,
    to_plain_dict,
)

logger = logging.getLogger("ok_service")

leave_ns = Namespace("leaves", description="Leaves management operations")


class LeaveCreatePayload(TypedDict):
    start_date: int
    end_date: int
    reason: str
    user: str
    responsible: str
    comment: str | None


class LeaveEditPayload(TypedDict, total=False):
    start_date: int
    end_date: int
    reason: str
    user: str
    responsible: str
    comment: str | None
    updated_by: str


class LeaveFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    user: str
    responsible: str
    reason: str
    date_from: int
    date_to: int
    deleted: bool


leave_ns.models[leave_create_model.name] = leave_create_model
leave_ns.models[leave_msg_model.name] = leave_msg_model
leave_ns.models[leave_response.name] = leave_response
leave_ns.models[leave_all_response.name] = leave_all_response
leave_ns.models[leave_model.name] = leave_model
leave_ns.models[leave_edit_model.name] = leave_edit_model
leave_ns.models[leave_reason_model.name] = leave_reason_model
leave_ns.models[leave_reason_all_response.name] = leave_reason_all_response


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


def _repository() -> SQLAlchemyLeaveRepository:
    return SQLAlchemyLeaveRepository(
        statistics=RedisProjectWorkStatistics(current_app.extensions["redis"])
    )


def _map_error(error: Exception):
    if isinstance(error, LeaveConflictError):
        payload: dict[str, object] = {"msg": str(error)}
        if error.detail is not None:
            payload["detail"] = error.detail
        return payload, 409
    if isinstance(error, LeaveNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete leave: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


def _parse_leave_id(leave_id: str) -> UUID:
    try:
        return UUID(leave_id)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _parse_reason(value: str | None) -> AbsenceReason | None:
    if value is None:
        return None
    return AbsenceReason(value)


@leave_ns.route("/add")
class LeaveAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @leave_ns.expect(leave_create_model, validate=False)
    @leave_ns.marshal_with(leave_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new leave", extra={"login": current_user})

        schema = LeaveCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(LeaveCreatePayload, schema.load(raw_payload))
            reason = _parse_reason(data["reason"])
            if reason is None:
                raise ValueError("Leave reason is required")
            command = CreateLeaveCommand(
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=reason,
                user_id=required_uuid(data["user"], "User is required"),
                responsible_id=required_uuid(
                    data["responsible"], "Responsible is required"
                ),
                created_by=required_uuid(
                    get_optional_str(current_user, "user_id"),
                    "Current user id is required",
                ),
                comment=get_optional_str(data, "comment"),
            )
            leave = CreateLeaveUseCase(repository=_repository()).execute(command)
            return {
                "msg": "New leave added successfully",
                "leave_id": str(leave.leave_id),
            }, 200
        except Exception as error:
            logger.error(f"Error adding leave: {error}", extra={"login": current_user})
            return _map_error(error)


@leave_ns.route("/<string:leave_id>/view")
class LeaveView(Resource):
    @api_key_or_jwt_required
    @leave_ns.marshal_with(leave_response)
    def get(self, leave_id):
        current_user = _get_current_user()
        logger.info(f"Request to view leave: {leave_id}", extra={"login": current_user})

        try:
            leave = GetLeaveUseCase(repository=_repository()).execute(
                _parse_leave_id(leave_id)
            )
            return {
                "msg": "Leave found successfully",
                "leave": leave_entity_to_response(leave),
            }, 200
        except Exception as error:
            logger.error(f"Error viewing leave: {error}", extra={"login": current_user})
            return _map_error(error)


@leave_ns.route("/<string:leave_id>/delete/soft")
class LeaveSoftDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @leave_ns.marshal_with(leave_msg_model)
    def patch(self, leave_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to soft delete leave: {leave_id}", extra={"login": current_user}
        )

        try:
            SoftDeleteLeaveUseCase(repository=_repository()).execute(
                _parse_leave_id(leave_id),
                updated_by=required_uuid(
                    get_optional_str(current_user, "user_id"),
                    "Current user id is required",
                ),
            )
            return {
                "msg": f"Leave {leave_id} soft deleted successfully",
                "leave_id": leave_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error soft deleting leave: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@leave_ns.route("/<string:leave_id>/delete/hard")
class LeaveHardDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @leave_ns.marshal_with(leave_msg_model)
    def delete(self, leave_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete leave: {leave_id}", extra={"login": current_user}
        )

        try:
            HardDeleteLeaveUseCase(repository=_repository()).execute(
                _parse_leave_id(leave_id)
            )
            return {
                "msg": f"Leave {leave_id} hard deleted successfully",
                "leave_id": leave_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting leave: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@leave_ns.route("/<string:leave_id>/edit")
class LeaveEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @leave_ns.expect(leave_edit_model, validate=False)
    @leave_ns.marshal_with(leave_msg_model)
    def patch(self, leave_id):
        current_user = _get_current_user()
        logger.info(f"Request to edit leave: {leave_id}", extra={"login": current_user})

        schema = LeaveEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(LeaveEditPayload, schema.load(raw_payload))
            reason = _parse_reason(get_optional_str(data, "reason"))
            command = UpdateLeaveCommand(
                leave_id=_parse_leave_id(leave_id),
                updated_by=required_uuid(
                    get_optional_str(current_user, "user_id"),
                    "Current user id is required",
                ),
                start_date=get_optional_int(data, "start_date"),
                end_date=get_optional_int(data, "end_date"),
                reason=reason,
                user_id=optional_uuid(get_optional_str(data, "user")),
                responsible_id=optional_uuid(get_optional_str(data, "responsible")),
                comment=get_optional_str(data, "comment"),
            )
            leave = UpdateLeaveUseCase(repository=_repository()).execute(command)
            return {
                "msg": "Leave edited successfully",
                "leave_id": str(leave.leave_id),
            }, 200
        except Exception as error:
            logger.error(f"Error editing leave: {error}", extra={"login": current_user})
            return _map_error(error)


@leave_ns.route("/all")
class LeaveAll(Resource):
    @api_key_or_jwt_required
    @leave_ns.expect(leave_filter_parser)
    @leave_ns.marshal_with(leave_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all leaves", extra={"login": current_user})

        schema = LeaveFilterSchema()
        try:
            args = cast(LeaveFilterPayload, schema.load(request.args.to_dict()))
            query = LeaveListQuery(
                offset=get_optional_int(args, "offset") or 0,
                limit=get_optional_int(args, "limit"),
                sort_by=get_optional_str(args, "sort_by") or "created_at",
                sort_order=get_optional_str(args, "sort_order") or "desc",
                user_id=optional_uuid(get_optional_str(args, "user")),
                responsible_id=optional_uuid(get_optional_str(args, "responsible")),
                reason=_parse_reason(get_optional_str(args, "reason")),
                date_from=get_optional_int(args, "date_from"),
                date_to=get_optional_int(args, "date_to"),
                deleted=get_optional_bool(args, "deleted"),
            )
            leaves = ListLeavesUseCase(repository=_repository()).execute(query)
            return {
                "msg": "Leaves found successfully",
                "leaves": [leave_entity_to_list_item(leave) for leave in leaves],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching leaves: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@leave_ns.route("/reasons/all")
class LeaveReasons(Resource):
    @api_key_or_jwt_required
    @leave_ns.marshal_with(leave_reason_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch leave reasons", extra={"login": current_user})

        reasons = ListAbsenceReasonsUseCase().execute()
        return {
            "msg": "Leave reasons found successfully",
            "reasons": [asdict(reason) for reason in reasons],
        }, 200
