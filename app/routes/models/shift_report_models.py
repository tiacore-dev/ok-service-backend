# Models for shift reports namespace
from flask_restx import Model, fields, reqparse


shift_report_create_model = Model('ShiftReportCreate', {
    "user": fields.String(required=True, description="User ID"),
    "date": fields.Integer(required=True, description="Report date"),
    "project": fields.String(required=True, description="Project ID"),
    "signed": fields.Boolean(required=True, description="Is the report signed"),
})


shift_report_model = Model('ShiftReport', {
    "shift_report_id": fields.String(required=True, description="ID of the shift report"),
    "user": fields.String(required=True, description="User details"),
    "date": fields.Integer(required=True, description="Report date"),
    "project": fields.String(required=True, description="Project details"),
    "signed": fields.Boolean(required=True, description="Is the report signed"),
    "deleted": fields.Boolean(required=True, description="Deletion status of the shift report")
})


shift_report_msg_model = Model('ShiftReportMessage', {
    "msg": fields.String(required=True, description="Response message")
})

shift_report_response = Model('ShiftReportResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "shift_report": fields.Nested(shift_report_model, required=True)
})

shift_report_all_response = Model('ShiftReportAllResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "shift_reports": fields.List(fields.Nested(shift_report_model), description="List of shift reports")
})

shift_report_filter_parser = reqparse.RequestParser()
shift_report_filter_parser.add_argument(
    'offset', type=int, default=0, help="Offset for pagination")
shift_report_filter_parser.add_argument(
    'limit', type=int, default=10, help="Limit for pagination")
shift_report_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Field for sorting')
shift_report_filter_parser.add_argument('sort_order', type=str, required=False, choices=[
    'asc', 'desc'], help='Sort order')
shift_report_filter_parser.add_argument(
    'user', type=str, help="Filter by user ID")
shift_report_filter_parser.add_argument(
    'date', type=int, help="Filter by date")
shift_report_filter_parser.add_argument(
    'project', type=str, help="Filter by project ID")
shift_report_filter_parser.add_argument(
    'deleted',
    # Интерпретация значения как логического
    type=lambda x: x.lower() in ['true', '1'],
    required=False,
    help="Флаг для фильтрации по удаленным отчетам"
)
