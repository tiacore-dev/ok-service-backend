# Models for shift report details namespace
from flask_restx import Model, fields, reqparse


shift_report_details_create_model = Model('ShiftReportDetailsCreate', {
    "shift_report": fields.String(required=True, description="Shift report ID"),
    "work": fields.String(required=True, description="Work ID"),
    "quantity": fields.Float(required=True, description="Quantity of work"),
    "summ": fields.Float(required=True, description="Total sum of work")
})

shift_report_details_model = Model('ShiftReportDetails', {
    "shift_report_details_id": fields.String(required=True, description="ID of the shift report detail"),
    "shift_report": fields.String(required=True, description="Shift report details"),
    "work": fields.String(required=True, description="Work details"),
    "quantity": fields.Float(required=True, description="Quantity of work"),
    "summ": fields.Float(required=True, description="Total sum of work")
})

shift_report_details_msg_model = Model('ShiftReportDetailsMessage', {
    "msg": fields.String(required=True, description="Response message")
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
    'work', type=str, help="Filter by work ID")
