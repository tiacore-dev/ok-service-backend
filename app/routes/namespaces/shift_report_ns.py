# Namespace for ShiftReports
import json
import logging
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.routes.models.shift_report_models import (
    shift_report_all_response,
    shift_report_create_model,
    shift_report_detail_model,
    shift_report_filter_parser,
    shift_report_model,
    shift_report_msg_model,
    shift_report_response,
)
from app.schemas.shift_report_schemas import (
    ShiftReportCreateSchema,
    ShiftReportEditSchema,
    ShiftReportFilterSchema,
)

logger = logging.getLogger("ok_service")

shift_report_ns = Namespace(
    "shift_reports", description="Shift reports management operations"
)


# Initialize models
shift_report_ns.models[shift_report_model.name] = shift_report_model
shift_report_ns.models[shift_report_detail_model.name] = shift_report_detail_model
shift_report_ns.models[shift_report_create_model.name] = shift_report_create_model
shift_report_ns.models[shift_report_msg_model.name] = shift_report_msg_model
shift_report_ns.models[shift_report_response.name] = shift_report_response
shift_report_ns.models[shift_report_all_response.name] = shift_report_all_response


@shift_report_ns.route("/add")
class ShiftReportAdd(Resource):
    @jwt_required()
    @shift_report_ns.expect(shift_report_create_model)
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to add new shift report", extra={"login": current_user})

        schema = ShiftReportCreateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"msg": "Validation error", "detail": err.messages}, 400
        try:
            from app.database.managers.shift_reports_managers import ShiftReportsManager

            db = ShiftReportsManager()

            if current_user["role"] == "user":
                data["user"] = current_user["user_id"]  # type: ignore
                data["signed"] = False  # type: ignore
            new_report = db.add_shift_report_with_details(
                # Returns a dictionary
                data,
                created_by=current_user["user_id"],
            )
            logger.info(
                f"New shift report added: {new_report['shift_report_id']}",
                extra={"login": current_user},
            )
            return {
                "msg": "New shift report added successfully",
                "shift_report_id": new_report["shift_report_id"],
            }, 200
        except ValueError as err:
            logger.warning(
                f"Shift report creation blocked: {err}", extra={"login": current_user}
            )
            return {"msg": str(err)}, 409
        except Exception as e:
            logger.error(
                f"Error adding shift report: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error adding shift report: {e}"}, 500


@shift_report_ns.route("/<string:report_id>/view")
class ShiftReportView(Resource):
    @jwt_required()
    @shift_report_ns.marshal_with(shift_report_response)
    def get(self, report_id):
        current_user = get_jwt_identity()
        logger.info(
            f"Request to view shift report: {report_id}", extra={"login": current_user}
        )
        try:
            try:
                report_id = UUID(report_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import ShiftReportsManager

            db = ShiftReportsManager()
            report = db.get_by_id(report_id)
            if not report:
                return {"msg": "Shift report not found"}, 404
            return {
                "msg": "Shift report found successfully",
                "shift_report": report,
            }, 200
        except Exception as e:
            logger.error(
                f"Error viewing shift report: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error viewing shift report: {e}"}, 500


@shift_report_ns.route("/<string:report_id>/delete/soft")
class ShiftReportSoftDelete(Resource):
    @jwt_required()
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def patch(self, report_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to soft delete shift report: {report_id}",
            extra={"login": current_user},
        )
        try:
            try:
                report_id = UUID(report_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import ShiftReportsManager

            db = ShiftReportsManager()

            # Проверки по ролям
            shift_report = db.get_by_id(record_id=report_id)
            if (
                shift_report["user"] != current_user["user_id"]  # type: ignore
                and current_user["role"] == "user"
            ):
                logger.warning(
                    "Trying to soft delete not user's shift report",
                    extra={"login": current_user},
                )
                return {"msg": "User cannot soft delete not his shift report"}, 403
            elif (
                shift_report["user"] == current_user["user_id"]  # type: ignore
                and shift_report["signed"] is True  # type: ignore
            ):
                logger.warning(
                    "Trying to soft delete signed shift report",
                    extra={"login": current_user},
                )
                return {"msg": "User cannot soft delete signed shift report"}, 403

            updated = db.update(record_id=report_id, deleted=True)
            if not updated:
                return {"msg": "Shift report not found"}, 404
            return {
                "msg": f"Shift report {report_id} soft deleted successfully",
                "shift_report_id": report_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error soft deleting shift report: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error soft deleting shift report: {e}"}, 500


@shift_report_ns.route("/<string:report_id>/delete/hard")
class ShiftReportHardDelete(Resource):
    @jwt_required()
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def delete(self, report_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to hard delete shift report: {report_id}",
            extra={"login": current_user},
        )
        try:
            try:
                report_id = UUID(report_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import ShiftReportsManager

            db = ShiftReportsManager()

            # Проверки по ролям
            shift_report = db.get_by_id(record_id=report_id)
            if (
                shift_report["user"] != current_user["user_id"]  # type: ignore
                and current_user["role"] == "user"
            ):
                logger.warning(
                    "Trying to hard delete not user's shift report",
                    extra={"login": current_user},
                )
                return {"msg": "User cannot hard delete not his shift report"}, 403
            elif (
                shift_report["user"] == current_user["user_id"]  # type: ignore
                and shift_report["signed"] is True  # type: ignore
            ):
                logger.warning(
                    "Trying to hard delete signed shift report",
                    extra={"login": current_user},
                )
                return {"msg": "User cannot hard delete signed shift report"}, 403

            deleted = db.delete(record_id=report_id)
            if not deleted:
                return {"msg": "Shift report not found"}, 404
            return {
                "msg": f"Shift report {report_id} hard deleted successfully",
                "shift_report_id": report_id,
            }, 200
        except IntegrityError:
            abort(409, description="Cannot delete shift report: dependent data exists.")
        except Exception as e:
            logger.error(
                f"Error hard deleting shift report: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error hard deleting shift report: {e}"}, 500


@shift_report_ns.route("/<string:report_id>/edit")
class ShiftReportEdit(Resource):
    @jwt_required()
    @shift_report_ns.expect(shift_report_create_model)
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def patch(self, report_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to edit shift report: {report_id}", extra={"login": current_user}
        )

        schema = ShiftReportEditSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            # Возвращаем 400 с описанием ошибки
            return {"msg": "Validation error", "detail": err.messages}, 400
        try:
            try:
                report_id = UUID(report_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import ShiftReportsManager

            db = ShiftReportsManager()

            # Проверки по ролям
            shift_report = db.get_by_id(record_id=report_id)
            if (
                shift_report["user"] != current_user["user_id"]  # type: ignore
                and current_user["role"] == "user"
            ):
                logger.warning(
                    "Trying to edit not user's shift report",
                    extra={"login": current_user},
                )
                return {"msg": "User cannot edit not his shift report"}, 403
            elif (
                shift_report["user"] == current_user["user_id"]  # type: ignore
                and shift_report["signed"] is True  # type: ignore
            ):
                logger.warning(
                    "Trying to edit signed shift report", extra={"login": current_user}
                )
                return {"msg": "User cannot edit signed shift report"}, 403

            target_user = data.get("user") or shift_report["user"]  # type: ignore

            def _resolve_date(field_name):
                """Возвращает значение поля даты с резервом на общее поле date."""
                if field_name in data and data.get(field_name) is not None:  # type: ignore
                    return data.get(field_name)  # type: ignore
                if shift_report.get(field_name) is not None:  # type: ignore
                    return shift_report.get(field_name)  # type: ignore
                # Если конкретное поле отсутствует, используем значение date
                base_date = (
                    data.get("date")  # type: ignore
                    if data.get("date") is not None  # type: ignore
                    else shift_report.get("date")  # type: ignore
                )
                return base_date

            target_date_start = _resolve_date("date_start")
            target_date_end = _resolve_date("date_end")

            from app.database.managers.leaves_manager import LeavesManager

            leaves_manager = LeavesManager()
            if (
                target_date_start is not None and target_date_end is not None
            ) and leaves_manager.has_overlapping_leave(
                target_user, target_date_start, target_date_end
            ):
                logger.warning(
                    "Shift edit intersects with existing leave",
                    extra={"login": current_user},
                )
                return {"msg": "Shift date intersects with existing leave"}, 409

            updated = db.update(record_id=report_id, **data)  # type: ignore
            if not updated:
                return {"msg": "Shift report not found"}, 404
            return {
                "msg": "Shift report updated successfully",
                "shift_report_id": report_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error editing shift report: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error editing shift report: {e}"}, 500


@shift_report_ns.route("/all")
class ShiftReportAll(Resource):
    @jwt_required()
    @shift_report_ns.expect(shift_report_filter_parser)
    @shift_report_ns.marshal_with(shift_report_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to fetch all shift reports", extra={"login": current_user})

        # Валидация query-параметров через Marshmallow
        schema = ShiftReportFilterSchema()
        raw_args = request.args.to_dict()
        user_args = request.args.getlist("user")
        project_args = request.args.getlist("project")
        if user_args:
            raw_args["user"] = user_args  # type: ignore
        if project_args:
            raw_args["project"] = project_args  # type: ignore
        try:
            args = schema.load(raw_args)  # Валидируем query-параметры
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            return {"msg": "Validation error", "detail": err.messages}, 400
        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", None)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        user_filter = args.get("user") or []  # type: ignore
        project_filter = args.get("project") or []  # type: ignore
        filters = {
            "user": [UUID(user_id) for user_id in user_filter] if user_filter else None,  # type: ignore
            "date_from": int(args.get("date_from")) if args.get("date_from") else None,  # type: ignore
            "date_to": int(args.get("date_to")) if args.get("date_to") else None,  # type: ignore
            "project": [UUID(project_id) for project_id in project_filter] if project_filter else None,  # type: ignore
            "lng_start": args.get("lng_start"),  # type: ignore
            "ltd_start": args.get("ltd_start"),  # type: ignore
            "lng_end": args.get("lng_end"),  # type: ignore
            "ltd_end": args.get("ltd_end"),  # type: ignore
            "distance_start": args.get("distance_start"),  # type: ignore
            "distance_end": args.get("distance_end"),  # type: ignore
            "created_by": args.get("created_by"),  # type: ignore
            "created_at": args.get("created_at"),  # type: ignore
            "deleted": args.get("deleted", None),  # type: ignore
        }
        if current_user["role"] == "user":
            filters["user"] = [UUID(current_user["user_id"])]

        if current_user["role"] == "project-leader":
            from app.database.managers.projects_managers import ProjectsManager

            project_manager = ProjectsManager()
            user_projects = project_manager.get_projects_by_leader(
                UUID(current_user["user_id"])
            )
            project_ids = [p["project_id"] for p in user_projects]
            if not filters["project"]:
                if not project_ids:
                    return {"msg": "No shift reports found", "shift_reports": []}, 200
                # Фильтруем только по проектам прораба
                filters["project"] = project_ids
            else:
                if any(proj not in project_ids for proj in filters["project"]):  # type: ignore
                    return {"msg": "Forbidden"}, 403

        logger.debug(
            f"Fetching shift reports with filters: {filters}, offset={offset}, limit={
                limit
            }",
            extra={"login": current_user},
        )

        try:
            from app.database.managers.shift_reports_managers import ShiftReportsManager

            db = ShiftReportsManager()
            total_count, reports = db.get_shift_reports_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(reports)} shift reports",
                extra={"login": current_user},
            )
            for report in reports:
                report["shift_report_details_sum"] = db.get_total_sum_by_shift_report(
                    report["shift_report_id"]
                )
            return {
                "msg": "Shift reports found successfully",
                "shift_reports": reports,
                "total": total_count,
            }, 200
        except Exception as e:
            logger.error(
                f"Error fetching shift reports: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error fetching shift reports: {e}"}, 500
