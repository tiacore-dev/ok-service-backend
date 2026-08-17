from __future__ import annotations

import json
import logging
from typing import Any, NotRequired, TypedDict, cast
from uuid import UUID

from flask import current_app, g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.shift_reports import (
    SQLAlchemyShiftReportRepository,
    shift_report_detail_entity_to_response,
    shift_report_entity_to_response,
)
from app.adapters.statistics import RedisProjectWorkStatistics
from app.decorators import api_key_or_jwt_required
from app.domain.shift_reports import (
    ShiftReportConflictError,
    ShiftReportForbiddenError,
    ShiftReportNotFoundError,
    ShiftReportValidationError,
)
from app.routes.models.shift_report_detail_models import (
    project_work_brief_model,
    shift_report_brief_model,
    shift_report_details_all_response,
    shift_report_details_by_report_ids,
    shift_report_details_create_model,
    shift_report_details_edit_model,
    shift_report_details_filter_parser,
    shift_report_details_many_msg_model,
    shift_report_details_model,
    shift_report_details_msg_model,
    shift_report_details_response,
)
from app.routes.models.shift_report_models import (
    shift_report_all_response,
    shift_report_create_model,
    shift_report_detail_model,
    shift_report_edit_model,
    shift_report_filter_parser,
    shift_report_model,
    shift_report_msg_model,
    shift_report_response,
    shift_report_updater_model,
    shift_report_user_model,
)
from app.schemas.shift_report_detail_schemas import (
    ShiftReportDetailsByReportsSchema,
    ShiftReportDetailsCreateSchema,
    ShiftReportDetailsEditSchema,
    ShiftReportDetailsFilterSchema,
)
from app.schemas.shift_report_schemas import (
    ShiftReportCreateSchema,
    ShiftReportEditSchema,
    ShiftReportFilterSchema,
)
from app.use_cases.shift_reports import (
    CreateShiftReportCommand,
    CreateShiftReportDetailCommand,
    CreateShiftReportDetailPayload,
    CreateShiftReportDetailUseCase,
    CreateShiftReportUseCase,
    DeleteShiftReportDetailUseCase,
    DeleteShiftReportUseCase,
    GetShiftReportDetailUseCase,
    GetShiftReportUseCase,
    ListShiftReportDetailsUseCase,
    ListShiftReportsUseCase,
    ShiftReportActor,
    ShiftReportListQuery,
    ShiftReportTimeCommand,
    SignShiftReportUseCase,
    SoftDeleteShiftReportUseCase,
    UpdateShiftReportCommand,
    UpdateShiftReportDetailCommand,
    UpdateShiftReportDetailUseCase,
    UpdateShiftReportTimeUseCase,
    UpdateShiftReportUseCase,
)
from app.web._typing import (
    get_optional_bool,
    get_optional_float,
    get_optional_int,
    get_optional_str,
    get_optional_uuid,
    get_optional_uuid_list,
    get_required_uuid,
    to_plain_dict,
)

logger = logging.getLogger("ok_service")

shift_report_ns = Namespace(
    "shift_reports", description="Shift reports management operations"
)
shift_report_details_ns = Namespace(
    "shift_report_details", description="Shift report details management operations"
)

shift_report_ns.models[shift_report_model.name] = shift_report_model
shift_report_ns.models[shift_report_user_model.name] = shift_report_user_model
shift_report_ns.models[shift_report_updater_model.name] = shift_report_updater_model
shift_report_ns.models[shift_report_detail_model.name] = shift_report_detail_model
shift_report_ns.models[shift_report_create_model.name] = shift_report_create_model
shift_report_ns.models[shift_report_edit_model.name] = shift_report_edit_model
shift_report_ns.models[shift_report_msg_model.name] = shift_report_msg_model
shift_report_ns.models[shift_report_response.name] = shift_report_response
shift_report_ns.models[shift_report_all_response.name] = shift_report_all_response

shift_report_details_ns.models[shift_report_details_create_model.name] = (
    shift_report_details_create_model
)
shift_report_details_ns.models[project_work_brief_model.name] = project_work_brief_model
shift_report_details_ns.models[shift_report_brief_model.name] = shift_report_brief_model
shift_report_details_ns.models[shift_report_details_edit_model.name] = (
    shift_report_details_edit_model
)
shift_report_details_ns.models[shift_report_details_msg_model.name] = (
    shift_report_details_msg_model
)
shift_report_details_ns.models[shift_report_details_response.name] = (
    shift_report_details_response
)
shift_report_details_ns.models[shift_report_details_all_response.name] = (
    shift_report_details_all_response
)
shift_report_details_ns.models[shift_report_details_model.name] = (
    shift_report_details_model
)
shift_report_details_ns.models[shift_report_details_many_msg_model.name] = (
    shift_report_details_many_msg_model
)
shift_report_details_ns.models[shift_report_details_by_report_ids.name] = (
    shift_report_details_by_report_ids
)


class ShiftReportCreatePayload(TypedDict):
    user: str
    date: int
    date_start: NotRequired[int | None]
    date_end: NotRequired[int | None]
    project: str
    lng_start: NotRequired[float | None]
    ltd_start: NotRequired[float | None]
    lng_end: NotRequired[float | None]
    ltd_end: NotRequired[float | None]
    distance_start: NotRequired[float | None]
    distance_end: NotRequired[float | None]
    signed: NotRequired[bool]
    night_shift: NotRequired[bool]
    extreme_conditions: NotRequired[bool]
    comment: NotRequired[str | None]


class ShiftReportEditPayload(TypedDict, total=False):
    user: str
    date: int
    date_start: int | None
    date_end: int | None
    project: str
    lng_start: float | None
    ltd_start: float | None
    lng_end: float | None
    ltd_end: float | None
    distance_start: float | None
    distance_end: float | None
    signed: bool
    night_shift: bool
    extreme_conditions: bool
    deleted: bool
    comment: str | None


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


def _repository() -> SQLAlchemyShiftReportRepository:
    return SQLAlchemyShiftReportRepository(
        statistics=RedisProjectWorkStatistics(current_app.extensions["redis"])
    )


def _actor(current_user: dict[str, Any]) -> ShiftReportActor:
    return ShiftReportActor(
        role=str(current_user.get("role") or ""),
        user_id=UUID(str(current_user["user_id"])),
    )


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _detail_response_with_stats(detail, repository, with_stat: bool = False):
    response = shift_report_detail_entity_to_response(detail)
    if not with_stat:
        return response
    project_work = response.get("project_work")
    if not project_work or detail.shift_report_project is None:
        return response
    stats = repository.get_project_stats(detail.shift_report_project).get(
        str(detail.work), {}
    )
    planned = float(stats.get("project_work_quantity", 0) or 0)
    actual = float(stats.get("shift_report_details_quantity", 0) or 0)
    project_work.update(
        project_work_quantity=planned,
        shift_report_details_quantity=actual,
        acceptance_status=(
            "not_checked"
            if actual == 0
            else "partial"
            if actual < planned
            else "accepted"
        ),
    )
    return response


def _build_list_query(data: dict[str, Any]) -> ShiftReportListQuery:
    return ShiftReportListQuery(
        offset=get_optional_int(data, "offset") or 0,
        limit=get_optional_int(data, "limit"),
        sort_by=get_optional_str(data, "sort_by") or "created_at",
        sort_order=get_optional_str(data, "sort_order") or "desc",
        user=get_optional_uuid_list(data, "user"),
        date_from=get_optional_int(data, "date_from"),
        date_to=get_optional_int(data, "date_to"),
        date_start_from=get_optional_int(data, "date_start_from"),
        date_start_to=get_optional_int(data, "date_start_to"),
        date_end_from=get_optional_int(data, "date_end_from"),
        date_end_to=get_optional_int(data, "date_end_to"),
        project=get_optional_uuid_list(data, "project"),
        lng_start=get_optional_float(data, "lng_start"),
        ltd_start=get_optional_float(data, "ltd_start"),
        lng_end=get_optional_float(data, "lng_end"),
        ltd_end=get_optional_float(data, "ltd_end"),
        distance_start=get_optional_float(data, "distance_start"),
        distance_end=get_optional_float(data, "distance_end"),
        night_shift=get_optional_bool(data, "night_shift"),
        extreme_conditions=get_optional_bool(data, "extreme_conditions"),
        signed=get_optional_bool(data, "signed"),
        deleted=get_optional_bool(data, "deleted"),
        comment=get_optional_str(data, "comment"),
    )


def _map_error(error: Exception):
    if isinstance(error, ShiftReportNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, ShiftReportForbiddenError):
        return {"msg": str(error)}, 403
    if isinstance(error, ShiftReportConflictError):
        return {"msg": str(error)}, 409
    if isinstance(error, ShiftReportValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete shift report: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@shift_report_ns.route("/add")
class ShiftReportAdd(Resource):
    @api_key_or_jwt_required
    @shift_report_ns.expect(shift_report_create_model, validate=False)
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new shift report", extra={"login": current_user})

        schema = ShiftReportCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ShiftReportCreatePayload, schema.load(raw_payload))
            details = data.get("details") or []
            command = CreateShiftReportCommand(
                user=get_required_uuid(data, "user", "User is required"),
                date=int(data["date"]),
                date_start=data.get("date_start"),
                date_end=data.get("date_end"),
                project=get_required_uuid(data, "project", "Project is required"),
                lng_start=data.get("lng_start"),
                ltd_start=data.get("ltd_start"),
                lng_end=data.get("lng_end"),
                ltd_end=data.get("ltd_end"),
                distance_start=data.get("distance_start"),
                distance_end=data.get("distance_end"),
                signed=bool(data.get("signed", False)),
                night_shift=bool(data.get("night_shift", False)),
                extreme_conditions=bool(data.get("extreme_conditions", False)),
                comment=data.get("comment"),
                details=[
                    CreateShiftReportDetailCommand(
                        project_work=get_optional_uuid(item, "project_work"),
                        work=get_required_uuid(item, "work", "Work is required"),
                        quantity=item["quantity"],
                    )
                    for item in details
                ]
                if details
                else None,
            )
            report = CreateShiftReportUseCase(repository=_repository()).execute(
                command, _actor(current_user)
            )
            return {
                "msg": "New shift report added successfully",
                "shift_report_id": str(report.shift_report_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding shift report: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@shift_report_ns.route("/<string:report_id>/view")
class ShiftReportView(Resource):
    @api_key_or_jwt_required
    @shift_report_ns.marshal_with(shift_report_response)
    def get(self, report_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view shift report: {report_id}", extra={"login": current_user}
        )
        try:
            report = GetShiftReportUseCase(repository=_repository()).execute(
                _parse_uuid(report_id)
            )
            response = shift_report_entity_to_response(report)
            response["shift_report_details_sum"] = (
                _repository().get_total_sum_by_shift_report(report.shift_report_id)
            )
            return {
                "msg": "Shift report found successfully",
                "shift_report": response,
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing shift report: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@shift_report_ns.route("/<string:report_id>/delete/soft")
class ShiftReportSoftDelete(Resource):
    @api_key_or_jwt_required
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def patch(self, report_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to soft delete shift report: {report_id}",
            extra={"login": current_user},
        )
        try:
            SoftDeleteShiftReportUseCase(repository=_repository()).execute(
                _parse_uuid(report_id), _actor(current_user)
            )
            return {
                "msg": f"Shift report {report_id} soft deleted successfully",
                "shift_report_id": report_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error soft deleting shift report: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_ns.route("/<string:report_id>/delete/hard")
class ShiftReportHardDelete(Resource):
    @api_key_or_jwt_required
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def delete(self, report_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete shift report: {report_id}",
            extra={"login": current_user},
        )
        try:
            DeleteShiftReportUseCase(repository=_repository()).execute(
                _parse_uuid(report_id), _actor(current_user)
            )
            return {
                "msg": f"Shift report {report_id} hard deleted successfully",
                "shift_report_id": report_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting shift report: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


def _update_shift_report_time(
    report_id: str, current_user: dict[str, Any], *, finish: bool
):
    raw_payload = to_plain_dict(
        request.get_json(silent=True), "Request body is required"
    )
    if not isinstance(raw_payload.get("lng"), (int, float)) or isinstance(
        raw_payload.get("lng"), bool
    ):
        raise ValueError("Field 'lng' must be a number")
    if not isinstance(raw_payload.get("ltd"), (int, float)) or isinstance(
        raw_payload.get("ltd"), bool
    ):
        raise ValueError("Field 'ltd' must be a number")
    command = ShiftReportTimeCommand(
        shift_report_id=_parse_uuid(report_id),
        actor_id=UUID(str(current_user["user_id"])),
        lng=float(raw_payload["lng"]),
        ltd=float(raw_payload["ltd"]),
    )
    use_case = UpdateShiftReportTimeUseCase(repository=_repository())
    updated = (
        use_case.finish(command, _actor(current_user))
        if finish
        else use_case.start(command, _actor(current_user))
    )
    return {
        "msg": "Shift report updated successfully",
        "shift_report_id": str(updated.shift_report_id),
    }, 200


@shift_report_ns.route("/<string:report_id>/start")
class ShiftReportStart(Resource):
    @api_key_or_jwt_required
    @shift_report_ns.expect(
        {"lng": fields.Float(required=True), "ltd": fields.Float(required=True)},
        validate=False,
    )
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def patch(self, report_id):
        current_user = _get_current_user()
        try:
            return _update_shift_report_time(report_id, current_user, finish=False)
        except Exception as error:
            return _map_error(error)


@shift_report_ns.route("/<string:report_id>/finish")
class ShiftReportFinish(Resource):
    @api_key_or_jwt_required
    @shift_report_ns.expect(
        {"lng": fields.Float(required=True), "ltd": fields.Float(required=True)},
        validate=False,
    )
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def patch(self, report_id):
        current_user = _get_current_user()
        try:
            return _update_shift_report_time(report_id, current_user, finish=True)
        except Exception as error:
            return _map_error(error)


@shift_report_ns.route("/<string:report_id>/sign")
class ShiftReportSign(Resource):
    @api_key_or_jwt_required
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def patch(self, report_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to sign shift report: {report_id}",
            extra={"login": current_user},
        )
        try:
            signed = SignShiftReportUseCase(repository=_repository()).execute(
                _parse_uuid(report_id), _actor(current_user)
            )
            return {
                "msg": "Shift report signed successfully",
                "shift_report_id": str(signed.shift_report_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error signing shift report: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_ns.route("/<string:report_id>/edit")
class ShiftReportEdit(Resource):
    @api_key_or_jwt_required
    @shift_report_ns.expect(shift_report_edit_model, validate=False)
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def patch(self, report_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit shift report: {report_id}", extra={"login": current_user}
        )
        schema = ShiftReportEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ShiftReportEditPayload, schema.load(raw_payload))
            updated = UpdateShiftReportUseCase(repository=_repository()).execute(
                UpdateShiftReportCommand(
                    shift_report_id=_parse_uuid(report_id),
                    user=get_optional_uuid(data, "user"),
                    date=get_optional_int(data, "date"),
                    date_start=get_optional_int(data, "date_start"),
                    date_end=get_optional_int(data, "date_end"),
                    project=get_optional_uuid(data, "project"),
                    lng_start=get_optional_float(data, "lng_start"),
                    ltd_start=get_optional_float(data, "ltd_start"),
                    lng_end=get_optional_float(data, "lng_end"),
                    ltd_end=get_optional_float(data, "ltd_end"),
                    distance_start=get_optional_float(data, "distance_start"),
                    distance_end=get_optional_float(data, "distance_end"),
                    signed=get_optional_bool(data, "signed"),
                    night_shift=get_optional_bool(data, "night_shift"),
                    extreme_conditions=get_optional_bool(data, "extreme_conditions"),
                    deleted=get_optional_bool(data, "deleted"),
                    comment=get_optional_str(data, "comment"),
                ),
                _actor(current_user),
            )
            return {
                "msg": "Shift report updated successfully",
                "shift_report_id": str(updated.shift_report_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing shift report: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@shift_report_ns.route("/all")
class ShiftReportAll(Resource):
    @api_key_or_jwt_required
    @shift_report_ns.expect(shift_report_filter_parser)
    @shift_report_ns.marshal_with(shift_report_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all shift reports", extra={"login": current_user})
        schema = ShiftReportFilterSchema()
        raw_args: dict[str, Any] = request.args.to_dict()
        if "user" in request.args:
            user_args = get_optional_uuid_list(
                {"user": request.args.getlist("user")}, "user"
            )
            if user_args is not None:
                raw_args["user"] = [str(item) for item in user_args]
        if "project" in request.args:
            project_args = get_optional_uuid_list(
                {"project": request.args.getlist("project")}, "project"
            )
            if project_args is not None:
                raw_args["project"] = [str(item) for item in project_args]
        try:
            args = cast(dict[str, Any], schema.load(raw_args))
        except ValidationError as err:
            return {"msg": "Validation error", "detail": err.messages}, 400
        try:
            total_count, reports = ListShiftReportsUseCase(
                repository=_repository()
            ).execute(
                _build_list_query(args),
                _actor(current_user),
            )
            response_reports = []
            repository = _repository()
            for report in reports:
                payload = shift_report_entity_to_response(report)
                payload["shift_report_details_sum"] = (
                    repository.get_total_sum_by_shift_report(report.shift_report_id)
                )
                response_reports.append(payload)
            return {
                "msg": "Shift reports found successfully",
                "shift_reports": response_reports,
                "total": total_count,
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching shift reports: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@shift_report_details_ns.route("/add/many")
class ShiftReportDetailsAddBulk(Resource):
    @api_key_or_jwt_required
    @shift_report_details_ns.expect([shift_report_details_create_model], validate=False)
    @shift_report_details_ns.marshal_with(shift_report_details_many_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info(
            "Request to add multiple shift report details",
            extra={"login": current_user},
        )
        schema = ShiftReportDetailsCreateSchema(many=True)
        try:
            raw_payload = request.get_json(silent=True)
            if not isinstance(raw_payload, list):
                raise ValueError("Request body is required")
            data_list = cast(list[dict[str, Any]], schema.load(raw_payload))
            use_case = CreateShiftReportDetailUseCase(repository=_repository())
            detail_ids = []
            for item in data_list:
                detail = use_case.execute(
                    CreateShiftReportDetailPayload(
                        shift_report=get_required_uuid(
                            item, "shift_report", "Shift report is required"
                        ),
                        project_work=get_optional_uuid(item, "project_work"),
                        work=get_required_uuid(item, "work", "Work is required"),
                        quantity=item["quantity"],
                        created_by=get_required_uuid(
                            current_user, "user_id", "Current user id is required"
                        ),
                    )
                )
                detail_ids.append(str(detail.shift_report_detail_id))
            return {
                "msg": "Shift report details added successfully",
                "shift_report_detail_ids": detail_ids,
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding shift report details: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_details_ns.route("/add")
class ShiftReportDetailsAdd(Resource):
    @api_key_or_jwt_required
    @shift_report_details_ns.expect(shift_report_details_create_model, validate=False)
    @shift_report_details_ns.marshal_with(shift_report_details_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info(
            "Request to add new shift report detail", extra={"login": current_user}
        )
        schema = ShiftReportDetailsCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(dict[str, Any], schema.load(raw_payload))
            detail = CreateShiftReportDetailUseCase(repository=_repository()).execute(
                CreateShiftReportDetailPayload(
                    shift_report=get_required_uuid(
                        data, "shift_report", "Shift report is required"
                    ),
                    project_work=get_optional_uuid(data, "project_work"),
                    work=get_required_uuid(data, "work", "Work is required"),
                    quantity=data["quantity"],
                    created_by=get_required_uuid(
                        current_user, "user_id", "Current user id is required"
                    ),
                )
            )
            return {
                "msg": "New shift report detail added successfully",
                "shift_report_detail_id": str(detail.shift_report_detail_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding shift report detail: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_details_ns.route("/<string:detail_id>/view")
class ShiftReportDetailsView(Resource):
    @api_key_or_jwt_required
    @shift_report_details_ns.marshal_with(shift_report_details_response)
    def get(self, detail_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view shift report detail: {detail_id}",
            extra={"login": current_user},
        )
        try:
            detail = GetShiftReportDetailUseCase(repository=_repository()).execute(
                _parse_uuid(detail_id)
            )
            return {
                "msg": "Shift report detail found successfully",
                "shift_report_detail": shift_report_detail_entity_to_response(detail),
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing shift report detail: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_details_ns.route("/<string:detail_id>/delete/hard")
class ShiftReportDetailsDelete(Resource):
    @api_key_or_jwt_required
    @shift_report_details_ns.marshal_with(shift_report_details_msg_model)
    def delete(self, detail_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to delete shift report detail: {detail_id}",
            extra={"login": current_user},
        )
        try:
            DeleteShiftReportDetailUseCase(repository=_repository()).execute(
                _parse_uuid(detail_id)
            )
            return {
                "msg": f"Shift report detail {detail_id} deleted successfully",
                "shift_report_detail_id": detail_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error deleting shift report detail: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_details_ns.route("/<string:detail_id>/edit")
class ShiftReportDetailsEdit(Resource):
    @api_key_or_jwt_required
    @shift_report_details_ns.expect(shift_report_details_edit_model, validate=False)
    @shift_report_details_ns.marshal_with(shift_report_details_msg_model)
    def patch(self, detail_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit shift report detail: {detail_id}",
            extra={"login": current_user},
        )
        schema = ShiftReportDetailsEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(dict[str, Any], schema.load(raw_payload))
            shift_report_value = data.get("shift_report")
            project_work_value = data.get("project_work")
            work_value = data.get("work")
            updated = UpdateShiftReportDetailUseCase(repository=_repository()).execute(
                UpdateShiftReportDetailCommand(
                    shift_report_detail_id=_parse_uuid(detail_id),
                    shift_report=_parse_uuid(str(shift_report_value))
                    if shift_report_value is not None
                    else None,
                    project_work=_parse_uuid(str(project_work_value))
                    if project_work_value is not None
                    else None,
                    work=_parse_uuid(str(work_value))
                    if work_value is not None
                    else None,
                    quantity=data.get("quantity"),
                )
            )
            return {
                "msg": "Shift report detail updated successfully",
                "shift_report_detail_id": str(updated.shift_report_detail_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing shift report detail: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_details_ns.route("/all")
class ShiftReportDetailsAll(Resource):
    @api_key_or_jwt_required
    @shift_report_details_ns.expect(shift_report_details_filter_parser)
    @shift_report_details_ns.response(
        200,
        "Shift report details found successfully",
        shift_report_details_all_response,
    )
    def get(self):
        current_user = _get_current_user()
        logger.info(
            "Request to fetch all shift report details", extra={"login": current_user}
        )
        schema = ShiftReportDetailsFilterSchema()
        raw_args: dict[str, Any] = request.args.to_dict()
        project_work_args = get_optional_uuid_list(
            {"project_work": request.args.getlist("project_work")}, "project_work"
        )
        if project_work_args is not None:
            raw_args["project_work"] = [str(item) for item in project_work_args]
        try:
            args = cast(dict[str, Any], schema.load(raw_args))
        except ValidationError as err:
            return {"error": err.messages}, 400
        try:
            details = ListShiftReportDetailsUseCase(repository=_repository()).execute(
                offset=args.get("offset", 0),
                limit=args.get("limit", 10),
                sort_by=args.get("sort_by"),
                sort_order=args.get("sort_order", "desc"),
                shift_report=args.get("shift_report"),
                date_from=args.get("date_from"),
                date_to=args.get("date_to"),
                work=args.get("work"),
                project_work=[
                    _parse_uuid(item) for item in (args.get("project_work") or [])
                ]
                if args.get("project_work")
                else None,
                min_quantity=args.get("min_quantity"),
                max_quantity=args.get("max_quantity"),
                min_summ=args.get("min_summ"),
                max_summ=args.get("max_summ"),
                created_by=args.get("created_by"),
                created_at=args.get("created_at"),
            )
            repository = _repository()
            return {
                "msg": "Shift report details found successfully",
                "shift_report_details": [
                    _detail_response_with_stats(
                        item, repository, with_stat=args.get("with_stat", False)
                    )
                    for item in details
                ],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching shift report details: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_details_ns.route("/all-by-reports")
class ShiftReportDetailsByReports(Resource):
    @api_key_or_jwt_required
    @shift_report_details_ns.expect(shift_report_details_by_report_ids, validate=False)
    @shift_report_details_ns.doc(consumes=["application/json"])
    @shift_report_details_ns.response(
        200,
        "Shift report details found successfully",
        shift_report_details_all_response,
    )
    def post(self):
        current_user = _get_current_user()
        logger.info(
            "Request to fetch shift report details by shift report ids",
            extra={"login": current_user},
        )
        schema = ShiftReportDetailsByReportsSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data_list = cast(dict[str, Any], schema.load(raw_payload))
            report_ids = data_list.get("shift_report_ids") or []
            repository = _repository()
            use_case = ListShiftReportDetailsUseCase(repository=repository)
            details = []
            for report_id in report_ids:
                matched = use_case.execute(shift_report=report_id)
                if matched:
                    details.extend(
                        _detail_response_with_stats(
                            item,
                            repository,
                            with_stat=data_list.get("with_stat", False),
                        )
                        for item in matched
                    )
            return {
                "msg": "Shift report details found successfully",
                "shift_report_details": details,
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching shift report details: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)
