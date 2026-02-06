# Namespace for ShiftReportDetails
import json
import logging
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.routes.models.shift_report_detail_models import (
    project_work_brief_model,
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
from app.schemas.shift_report_detail_schemas import (
    ShiftReportDetailsByReportsSchema,
    ShiftReportDetailsCreateSchema,
    ShiftReportDetailsEditSchema,
    ShiftReportDetailsFilterSchema,
)

logger = logging.getLogger("ok_service")

shift_report_details_ns = Namespace(
    "shift_report_details", description="Shift report details management operations"
)

# Initialize models
shift_report_details_ns.models[shift_report_details_create_model.name] = (
    shift_report_details_create_model
)
shift_report_details_ns.models[project_work_brief_model.name] = (
    project_work_brief_model
)
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


@shift_report_details_ns.route("/add/many")
class ShiftReportDetailsAddBulk(Resource):
    @jwt_required()
    @shift_report_details_ns.expect([shift_report_details_create_model])
    @shift_report_details_ns.marshal_with(shift_report_details_many_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            "Request to add multiple shift report details",
            extra={"login": current_user},
        )

        schema = ShiftReportDetailsCreateSchema(
            many=True
        )  # Используем валидацию списка
        try:
            data_list = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            return {"error": err.messages}, 400

        try:
            from app.database.managers.shift_reports_managers import (
                ShiftReportsDetailsManager,
            )

            db = ShiftReportsDetailsManager()

            shift_report_detail_ids = []

            for data in data_list:  # type: ignore
                new_detail = db.add_shift_report_deatails(
                    created_by=current_user["user_id"], **data
                )
                shift_report_detail_ids.append(new_detail["shift_report_detail_id"])

            logger.info(
                f"Added multiple shift report details: {shift_report_detail_ids}",
                extra={"login": current_user},
            )

            return {
                "msg": "Shift report details added successfully",
                "shift_report_detail_ids": shift_report_detail_ids,
            }, 200

        except Exception as e:
            logger.error(
                f"Error adding shift report details: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error adding shift report details: {e}"}, 500


@shift_report_details_ns.route("/add")
class ShiftReportDetailsAdd(Resource):
    @jwt_required()
    @shift_report_details_ns.expect(shift_report_details_create_model)
    @shift_report_details_ns.marshal_with(shift_report_details_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            "Request to add new shift report detail", extra={"login": current_user}
        )

        schema = ShiftReportDetailsCreateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            return {"error": err.messages}, 400
        try:
            from app.database.managers.shift_reports_managers import (
                ShiftReportsDetailsManager,
            )

            db = ShiftReportsDetailsManager()

            # Add shift report detail
            # Returns a dictionary
            new_detail = db.add_shift_report_deatails(
                created_by=current_user["user_id"],
                **data,  # type: ignore
            )
            logger.info(
                f"New shift report detail added: {
                    new_detail['shift_report_detail_id']
                }",
                extra={"login": current_user},
            )
            return {
                "msg": "New shift report detail added successfully",
                "shift_report_detail_id": new_detail["shift_report_detail_id"],
            }, 200
        except Exception as e:
            logger.error(
                f"Error adding shift report detail: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error adding shift report detail: {e}"}, 500


@shift_report_details_ns.route("/<string:detail_id>/view")
class ShiftReportDetailsView(Resource):
    @jwt_required()
    @shift_report_details_ns.marshal_with(shift_report_details_response)
    def get(self, detail_id):
        current_user = get_jwt_identity()
        logger.info(
            f"Request to view shift report detail: {detail_id}",
            extra={"login": current_user},
        )
        try:
            try:
                detail_id = UUID(detail_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import (
                ShiftReportsDetailsManager,
            )

            db = ShiftReportsDetailsManager()
            detail = db.get_by_id(detail_id)
            if not detail:
                logger.warning(
                    "Shift report detail not found", extra={"login": current_user}
                )
                return {"msg": "Shift report detail not found"}, 404
            return {
                "msg": "Shift report detail found successfully",
                "shift_report_detail": detail,
            }, 200
        except Exception as e:
            logger.error(
                f"Error viewing shift report detail: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error viewing shift report detail: {e}"}, 500


@shift_report_details_ns.route("/<string:detail_id>/delete/hard")
class ShiftReportDetailsDelete(Resource):
    @jwt_required()
    @shift_report_details_ns.marshal_with(shift_report_details_msg_model)
    def delete(self, detail_id):
        current_user = get_jwt_identity()
        logger.info(
            f"Request to delete shift report detail: {detail_id}",
            extra={"login": current_user},
        )
        try:
            try:
                detail_id = UUID(detail_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import (
                ShiftReportsDetailsManager,
            )

            db = ShiftReportsDetailsManager()
            deleted = db.delete(record_id=detail_id)
            if not deleted:
                logger.warning(
                    "Shift report detail not found", extra={"login": current_user}
                )
                return {"msg": "Shift report detail not found"}, 404
            return {
                "msg": f"Shift report detail {detail_id} deleted successfully",
                "shift_report_detail_id": detail_id,
            }, 200
        except IntegrityError:
            logger.warning(
                "Cannot delete shift report detail: dependent data exists",
                extra={"login": current_user},
            )
            abort(
                409,
                description="Cannot delete shift report detail: dependent data exists.",
            )
        except Exception as e:
            logger.error(
                f"Error deleting shift report detail: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error deleting shift report detail: {e}"}, 500


@shift_report_details_ns.route("/<string:detail_id>/edit")
class ShiftReportDetailsEdit(Resource):
    @jwt_required()
    @shift_report_details_ns.expect(shift_report_details_edit_model)
    @shift_report_details_ns.marshal_with(shift_report_details_msg_model)
    def patch(self, detail_id):
        current_user = get_jwt_identity()
        logger.info(
            f"Request to edit shift report detail: {detail_id}",
            extra={"login": current_user},
        )

        schema = ShiftReportDetailsEditSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        try:
            try:
                detail_id = UUID(detail_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import (
                ShiftReportsDetailsManager,
            )

            db = ShiftReportsDetailsManager()
            updated = db.update_shift_report_details(
                shift_report_detail_id=detail_id,
                **data,  # type: ignore
            )
            if not updated:
                logger.warning(
                    "Shift report detail not found", extra={"login": current_user}
                )
                return {"msg": "Shift report detail not found"}, 404
            return {
                "msg": "Shift report detail updated successfully",
                "shift_report_detail_id": detail_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error editing shift report detail: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error editing shift report detail: {e}"}, 500


@shift_report_details_ns.route("/all")
class ShiftReportDetailsAll(Resource):
    @jwt_required()
    @shift_report_details_ns.expect(shift_report_details_filter_parser)
    @shift_report_details_ns.marshal_with(shift_report_details_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info(
            "Request to fetch all shift report details", extra={"login": current_user}
        )

        # Валидация query-параметров через Marshmallow
        schema = ShiftReportDetailsFilterSchema()
        raw_args = request.args.to_dict()
        project_work_args = request.args.getlist("project_work")
        if project_work_args:
            raw_args["project_work"] = project_work_args  # type: ignore
        try:
            args = schema.load(raw_args)  # Валидируем query-параметры
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            return {"error": err.messages}, 400
        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", 10)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        project_work_filter = args.get("project_work") or []  # type: ignore
        filters = {
            "shift_report": args.get("shift_report"),  # type: ignore
            "work": args.get("work"),  # type: ignore
            "project_work": [UUID(work_id) for work_id in project_work_filter]
            if project_work_filter
            else None,  # type: ignore
            "min_quantity": args.get("min_quantity"),  # type: ignore
            "max_quantity": args.get("max_quantity"),  # type: ignore
            "min_summ": args.get("min_summ"),  # type: ignore
            "max_summ": args.get("max_summ"),  # type: ignore
            "created_by": args.get("created_by"),  # type: ignore
            "created_at": args.get("created_at"),  # type: ignore
        }

        logger.debug(
            f"Fetching shift report details with filters: {filters}, offset={
                offset
            }, limit={limit}",
            extra={"login": current_user},
        )

        try:
            from app.database.managers.shift_reports_managers import (
                ShiftReportsDetailsManager,
            )

            db = ShiftReportsDetailsManager()
            details = db.get_all_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(details)} shift report details",
                extra={"login": current_user},
            )
            return {
                "msg": "Shift report details found successfully",
                "shift_report_details": details,
            }, 200
        except Exception as e:
            logger.error(
                f"Error fetching shift report details: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error fetching shift report details: {e}"}, 500


@shift_report_details_ns.route("/all-by-reports")
class ShiftReportDetailsByReports(Resource):
    @jwt_required()
    @shift_report_details_ns.expect(shift_report_details_by_report_ids, validate=True)
    @shift_report_details_ns.doc(consumes=["application/json"])
    @shift_report_details_ns.marshal_with(shift_report_details_all_response)
    def post(self):
        current_user = get_jwt_identity()
        logger.info(
            "Request to fetch shift report details by shift report ids",
            extra={"login": current_user},
        )

        # Валидация query-параметров через Marshmallow
        schema = ShiftReportDetailsByReportsSchema()
        try:
            data_list = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.warning(
                "Validation failed for shift report ids",
                extra={"login": current_user, "errors": err.messages},
            )
            return {"error": err.messages}, 400

        report_ids = data_list.get("shift_report_ids") or []  # type: ignore
        details = []
        try:
            from app.database.managers.shift_reports_managers import (
                ShiftReportsDetailsManager,
            )

            db = ShiftReportsDetailsManager()
            for report_id in report_ids:
                detail = db.filter_one_by_dict(shift_report=report_id)
                if detail:
                    details.append(detail)
                else:
                    logger.warning(
                        f"No detail found for shift_report_id: {report_id}",
                        extra={"login": current_user},
                    )

            logger.info(
                f"Successfully fetched {len(details)} shift report details",
                extra={"login": current_user},
            )
            return {
                "msg": "Shift report details found successfully",
                "shift_report_details": details,
            }, 200
        except Exception as e:
            logger.error(
                f"Error fetching shift report details: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error fetching shift report details: {e}"}, 500
