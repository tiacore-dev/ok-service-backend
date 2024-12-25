# Namespace for ShiftReportDetails
import logging
from uuid import UUID
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.models.shift_report_detail_models import (
    shift_report_details_create_model,
    shift_report_details_msg_model,
    shift_report_details_response,
    shift_report_details_all_response,
    shift_report_details_model,
    shift_report_details_filter_parser
    # shift_report_model,
    # work_model
)

logger = logging.getLogger('ok_service')

shift_report_details_ns = Namespace(
    'shift_report_details', description='Shift report details management operations')

# Initialize models
shift_report_details_ns.models[shift_report_details_create_model.name] = shift_report_details_create_model
shift_report_details_ns.models[shift_report_details_msg_model.name] = shift_report_details_msg_model
shift_report_details_ns.models[shift_report_details_response.name] = shift_report_details_response
shift_report_details_ns.models[shift_report_details_all_response.name] = shift_report_details_all_response
shift_report_details_ns.models[shift_report_details_model.name] = shift_report_details_model
# shift_report_details_ns.models[shift_report_model.name] = shift_report_model
# shift_report_details_ns.models[work_model.name] = work_model


@shift_report_details_ns.route('/add')
class ShiftReportDetailsAdd(Resource):
    @jwt_required()
    @shift_report_details_ns.expect(shift_report_details_create_model)
    @shift_report_details_ns.marshal_with(shift_report_details_msg_model)
    def post(self):
        current_user = get_jwt_identity()
        logger.info("Request to add new shift report detail",
                    extra={"login": current_user})

        data = request.json
        try:
            from app.database.managers.shift_reports_managers import ShiftReportsDetailsManager
            db = ShiftReportsDetailsManager()

            # Add shift report detail
            new_detail = db.add(**data)  # Returns a dictionary
            logger.info(f"New shift report detail added: {new_detail['shift_report_details_id']}",
                        extra={"login": current_user})
            return {"msg": "New shift report detail added successfully"}, 200
        except Exception as e:
            logger.error(f"Error adding shift report detail: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error adding shift report detail: {e}"}, 500


@shift_report_details_ns.route('/<string:detail_id>/view')
class ShiftReportDetailsView(Resource):
    @jwt_required()
    @shift_report_details_ns.marshal_with(shift_report_details_response)
    def get(self, detail_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to view shift report detail: {detail_id}",
                    extra={"login": current_user})
        try:
            try:
                detail_id = UUID(detail_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import ShiftReportsDetailsManager
            db = ShiftReportsDetailsManager()
            detail = db.get_by_id(detail_id)
            if not detail:
                return {"msg": "Shift report detail not found"}, 404
            return {"msg": "Shift report detail found successfully", "shift_report_detail": detail}, 200
        except Exception as e:
            logger.error(f"Error viewing shift report detail: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error viewing shift report detail: {e}"}, 500


@shift_report_details_ns.route('/<string:detail_id>/delete')
class ShiftReportDetailsDelete(Resource):
    @jwt_required()
    @shift_report_details_ns.marshal_with(shift_report_details_msg_model)
    def delete(self, detail_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to delete shift report detail: {detail_id}",
                    extra={"login": current_user})
        try:
            try:
                detail_id = UUID(detail_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import ShiftReportsDetailsManager
            db = ShiftReportsDetailsManager()
            deleted = db.delete(record_id=detail_id)
            if not deleted:
                return {"msg": "Shift report detail not found"}, 404
            return {"msg": f"Shift report detail {detail_id} deleted successfully"}, 200
        except Exception as e:
            logger.error(f"Error deleting shift report detail: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error deleting shift report detail: {e}"}, 500


@shift_report_details_ns.route('/<string:detail_id>/edit')
class ShiftReportDetailsEdit(Resource):
    @jwt_required()
    @shift_report_details_ns.expect(shift_report_details_create_model)
    @shift_report_details_ns.marshal_with(shift_report_details_msg_model)
    def patch(self, detail_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to edit shift report detail: {detail_id}",
                    extra={"login": current_user})

        data = request.json
        try:
            try:
                detail_id = UUID(detail_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.shift_reports_managers import ShiftReportsDetailsManager
            db = ShiftReportsDetailsManager()
            updated = db.update(record_id=detail_id, **data)
            if not updated:
                return {"msg": "Shift report detail not found"}, 404
            return {"msg": "Shift report detail updated successfully"}, 200
        except Exception as e:
            logger.error(f"Error editing shift report detail: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error editing shift report detail: {e}"}, 500


@shift_report_details_ns.route('/all')
class ShiftReportDetailsAll(Resource):
    @jwt_required()
    @shift_report_details_ns.expect(shift_report_details_filter_parser)
    @shift_report_details_ns.marshal_with(shift_report_details_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info("Request to fetch all shift report details",
                    extra={"login": current_user})

        args = shift_report_details_filter_parser.parse_args()
        offset = args.get('offset', 0)
        limit = args.get('limit', 10)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'asc')
        filters = {
            'shift_report': args.get('shift_report'),
            'work': args.get('work')
        }

        logger.debug(f"Fetching shift report details with filters: {filters}, offset={offset}, limit={limit}",
                     extra={"login": current_user})

        try:
            from app.database.managers.shift_reports_managers import ShiftReportsDetailsManager
            db = ShiftReportsDetailsManager()
            details = db.get_all_filtered(
                offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order, **filters)
            logger.info(f"Successfully fetched {len(details)} shift report details",
                        extra={"login": current_user})
            return {"msg": "Shift report details found successfully", "shift_report_details": details}, 200
        except Exception as e:
            logger.error(f"Error fetching shift report details: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error fetching shift report details: {e}"}, 500
