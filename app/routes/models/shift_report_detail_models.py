# Models for shift report details namespace
from flask_restx import Model, fields, reqparse
from app.schemas.shift_report_detail_schemas import (
    ShiftReportDetailsCreateSchema,
    ShiftReportDetailsEditSchema,
)
from app.utils.helpers import generate_swagger_model

# Модель для создания проекта
shift_report_details_create_model = generate_swagger_model(
    ShiftReportDetailsCreateSchema(), "ShiftReportDetailsCreate")

shift_report_details_edit_model = generate_swagger_model(
    ShiftReportDetailsEditSchema(), "ShiftReportDetailsEdit")

shift_report_details_model = Model('ShiftReportDetails', {
    "shift_report_detail_id": fields.String(required=True, description="ID of the shift report detail"),
    "shift_report": fields.String(required=True, description="Shift report details"),
    "project_work": fields.String(required=False, description="Project work"),
    "work": fields.String(required=True, description="Work details"),
    "quantity": fields.Float(required=True, description="Quantity of work"),
    "created_at": fields.Integer(required=True, description="Date shift report detail was created at"),
    "created_by": fields.String(required=True, description="Creator of shift report detail"),
    "summ": fields.Float(required=True, description="Total sum of work")
})

shift_report_details_msg_model = Model('ShiftReportDetailsMessage', {
    "msg": fields.String(required=True, description="Response message"),
    "shift_report_detail_id": fields.String(description="ID of shift report detail")
})

shift_report_details_many_msg_model = Model('ShiftReportDetailsManyMessage', {
    "msg": fields.String(required=True, description="Response message"),
    "shift_report_detail_ids": fields.List(fields.String, description="List of shift report details")
})

shift_report_details_by_report_ids = Model('ShiftReportDetailsByIds', {
    "shift_report_ids": fields.List(fields.String, description="List of shift reports to fetch details")
})


shift_report_details_response = Model('ShiftReportDetailsResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "shift_report_detail": fields.Nested(shift_report_details_model, required=True)
})

shift_report_details_all_response = Model('ShiftReportDetailsAllResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "shift_report_details": fields.List(fields.Nested(shift_report_details_model), description="List of shift report details")
})

shift_report_details_filter_parser = reqparse.RequestParser()
shift_report_details_filter_parser.add_argument(
    'offset', type=int, default=0, help="Offset for pagination")
shift_report_details_filter_parser.add_argument(
    'limit', type=int, default=10, help="Limit for pagination")
shift_report_details_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Field for sorting')
shift_report_details_filter_parser.add_argument('sort_order', type=str, required=False, choices=[
    'asc', 'desc'], help='Sort order')
shift_report_details_filter_parser.add_argument(
    'shift_report', type=str, help="Filter by shift report ID")
shift_report_details_filter_parser.add_argument(
    'project_work', type=str, help="Filter by project work id")
shift_report_details_filter_parser.add_argument(
    'work', type=str, help="Filter by work ID")
shift_report_details_filter_parser.add_argument(
    'min_quantity', type=float, required=False, help="Minimum quantity filter"
)
shift_report_details_filter_parser.add_argument(
    'max_quantity', type=float, required=False, help="Maximum quantity filter"
)
shift_report_details_filter_parser.add_argument(
    'min_summ', type=float, required=False, help="Minimum summ filter"
)
shift_report_details_filter_parser.add_argument(
    'max_summ', type=float, required=False, help="Maximum summ filter"
)
