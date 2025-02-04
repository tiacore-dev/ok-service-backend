# Namespace for ShiftReports
# Namespace for ShiftReports
import logging
from uuid import UUID
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app.schemas.shift_report_schemas import ShiftReportCreateSchema, ShiftReportFilterSchema, ShiftReportEditSchema
from app.routes.models.shift_report_models import (
    shift_report_detail_model,
    shift_report_create_model,
    shift_report_msg_model,
    shift_report_response,
    shift_report_all_response,
    shift_report_filter_parser,
    shift_report_model
)

logger = logging.getLogger('ok_service')

shift_report_ns = Namespace(
    'shift_reports', description='Shift reports management operations')

print("Регистрируем shift_report_detail_model:", shift_report_detail_model)
print("Регистрируем shift_report_create_model:", shift_report_create_model)


# Initialize models
shift_report_ns.models[shift_report_model.name] = shift_report_model
shift_report_ns.models[shift_report_detail_model.name] = shift_report_detail_model
shift_report_ns.models[shift_report_create_model.name] = shift_report_create_model
shift_report_ns.models[shift_report_msg_model.name] = shift_report_msg_model
shift_report_ns.models[shift_report_response.name] = shift_report_response
shift_report_ns.models[shift_report_all_response.name] = shift_report_all_response


@shift_report_ns.route('/add')
class ShiftReportAdd(Resource):
    @jwt_required()
    @shift_report_ns.expect(shift_report_create_model)
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def post(self):
        current_user = get_jwt_identity()
        logger.info("Request to add new shift report",
                    extra={"login": current_user})

        schema = ShiftReportCreateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        try:
            from app.database.managers.shift_reports_managers import ShiftReportsManager
            db = ShiftReportsManager()

            # Add shift report
            new_report = db.add_shift_report_with_details(
                data)  # Returns a dictionary
            logger.info(f"New shift report added: {new_report['shift_report_id']}",
                        extra={"login": current_user})
            return {"msg": "New shift report added successfully", "shift_report_id": new_report['shift_report_id']}, 200
        except Exception as e:
            logger.error(f"Error adding shift report: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error adding shift report: {e}"}, 500


@shift_report_ns.route('/<string:report_id>/view')
class ShiftReportView(Resource):
    @jwt_required()
    @shift_report_ns.marshal_with(shift_report_response)
    def get(self, report_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to view shift report: {report_id}",
                    extra={"login": current_user})
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
            return {"msg": "Shift report found successfully", "shift_report": report}, 200
        except Exception as e:
            logger.error(f"Error viewing shift report: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error viewing shift report: {e}"}, 500


@shift_report_ns.route('/<string:report_id>/delete/soft')
class ShiftReportSoftDelete(Resource):
    @jwt_required()
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def patch(self, report_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to soft delete shift report: {report_id}",
                    extra={"login": current_user})
        try:
            try:
                report_id = UUID(report_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import ShiftReportsManager
            db = ShiftReportsManager()
            updated = db.update(record_id=report_id, deleted=True)
            if not updated:
                return {"msg": "Shift report not found"}, 404
            return {"msg": f"Shift report {report_id} soft deleted successfully", "shift_report_id": report_id}, 200
        except Exception as e:
            logger.error(f"Error soft deleting shift report: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error soft deleting shift report: {e}"}, 500


@shift_report_ns.route('/<string:report_id>/delete/hard')
class ShiftReportHardDelete(Resource):
    @jwt_required()
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def delete(self, report_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to hard delete shift report: {report_id}",
                    extra={"login": current_user})
        try:
            try:
                report_id = UUID(report_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import ShiftReportsManager
            db = ShiftReportsManager()
            deleted = db.delete(record_id=report_id)
            if not deleted:
                return {"msg": "Shift report not found"}, 404
            return {"msg": f"Shift report {report_id} hard deleted successfully", "shift_report_id": report_id}, 200
        except Exception as e:
            logger.error(f"Error hard deleting shift report: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error hard deleting shift report: {e}"}, 500


@shift_report_ns.route('/<string:report_id>/edit')
class ShiftReportEdit(Resource):
    @jwt_required()
    @shift_report_ns.expect(shift_report_create_model)
    @shift_report_ns.marshal_with(shift_report_msg_model)
    def patch(self, report_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to edit shift report: {report_id}",
                    extra={"login": current_user})

        schema = ShiftReportEditSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            logger.error(f"Validation error: {err.messages}")
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        try:
            try:
                report_id = UUID(report_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import ShiftReportsManager
            db = ShiftReportsManager()
            updated = db.update(record_id=report_id, **data)
            if not updated:
                return {"msg": "Shift report not found"}, 404
            return {"msg": "Shift report updated successfully", "shift_report_id": report_id}, 200
        except Exception as e:
            logger.error(f"Error editing shift report: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error editing shift report: {e}"}, 500


@shift_report_ns.route('/all')
class ShiftReportAll(Resource):
    @jwt_required()
    @shift_report_ns.expect(shift_report_filter_parser)
    @shift_report_ns.marshal_with(shift_report_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info("Request to fetch all shift reports",
                    extra={"login": current_user})

        # Валидация query-параметров через Marshmallow
        schema = ShiftReportFilterSchema()
        try:
            args = schema.load(request.args)  # Валидируем query-параметры
        except ValidationError as err:
            logger.error(f"Validation error: {err.messages}", extra={
                         "login": current_user})
            return {"error": err.messages}, 400
        offset = args.get('offset', 0)
        limit = args.get('limit', None)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'asc')
        filters = {
            'user': UUID(args.get('user')) if args.get('user') else None,
            'date': int(args.get('date')) if args.get('date') else None,
            'project': UUID(args.get('project')) if args.get('project') else None,
            'deleted': args.get('deleted', None)
        }

        logger.debug(f"Fetching shift reports with filters: {filters}, offset={offset}, limit={limit}",
                     extra={"login": current_user})

        try:
            from app.database.managers.shift_reports_managers import ShiftReportsManager
            db = ShiftReportsManager()
            reports = db.get_all_filtered(
                offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order, **filters)
            logger.info(f"Successfully fetched {len(reports)} shift reports",
                        extra={"login": current_user})
            for report in reports:
                report['shift_report_details_sum'] = db.get_total_sum_by_shift_report(
                    report['shift_report_id'])
            return {"msg": "Shift reports found successfully", "shift_reports": reports}, 200
        except Exception as e:
            logger.error(f"Error fetching shift reports: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error fetching shift reports: {e}"}, 500
