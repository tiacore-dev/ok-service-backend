# Models for shift reports namespace
from flask_restx import Model, fields, reqparse

from app.schemas.shift_report_schemas import (
    ShiftReportCreateSchema,
    ShiftReportDetailSchema,
)
from app.utils.helpers import generate_swagger_model

# 1. Создаем модель `ShiftReportDetail`
shift_report_detail_model = generate_swagger_model(
    ShiftReportDetailSchema,  # type: ignore
    "ShiftReportDetail",
)


# 3. Теперь создаем `ShiftReportCreate`, где `ShiftReportDetail` вложен
shift_report_create_model = generate_swagger_model(
    ShiftReportCreateSchema(), "ShiftReportCreate"
)


shift_report_model = Model(
    "ShiftReport",
    {
        "shift_report_id": fields.String(
            required=True, description="ID of the shift report"
        ),
        "user": fields.String(required=True, description="User details"),
        "date": fields.Integer(required=True, description="Report date"),
        "project": fields.String(required=True, description="Project details"),
        "signed": fields.Boolean(required=True, description="Is the report signed"),
        "deleted": fields.Boolean(
            required=True, description="Deletion status of the shift report"
        ),
        "number": fields.Integer(required=True, description="Number of shift report"),
        "created_at": fields.Integer(
            required=True, description="Date shift report was created at"
        ),
        "created_by": fields.String(
            required=True, description="Creator of shift report"
        ),
        "night_shift": fields.Boolean(required=True, description="Night shift"),
        "extreme_conditions": fields.Boolean(
            required=True, description="Extreme conditions"
        ),
        "shift_report_details_sum": fields.Float(
            required=False, description="Sum of shift_report_details"
        ),
    },
)


shift_report_msg_model = Model(
    "ShiftReportMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
        "shift_report_id": fields.String(description="ID of shift report"),
    },
)

shift_report_response = Model(
    "ShiftReportResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "shift_report": fields.Nested(shift_report_model, required=True),
    },
)

shift_report_all_response = Model(
    "ShiftReportAllResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "shift_reports": fields.List(
            fields.Nested(shift_report_model), description="List of shift reports"
        ),
        "total": fields.Integer(description="Total count of shift reports"),
    },
)

shift_report_filter_parser = reqparse.RequestParser()
shift_report_filter_parser.add_argument(
    "offset", type=int, default=0, help="Offset for pagination"
)
shift_report_filter_parser.add_argument(
    "limit", type=int, default=10, help="Limit for pagination"
)
shift_report_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Field for sorting"
)
shift_report_filter_parser.add_argument(
    "sort_order", type=str, required=False, choices=["asc", "desc"], help="Sort order"
)
shift_report_filter_parser.add_argument("user", type=str, help="Filter by user ID")
shift_report_filter_parser.add_argument("date_from", type=int, help="Filter by date")
shift_report_filter_parser.add_argument("date_to", type=int, help="Filter by date")
shift_report_filter_parser.add_argument(
    "project", type=str, help="Filter by project ID"
)
shift_report_filter_parser.add_argument(
    "night_shift",
    # Интерпретация значения как логического
    type=lambda x: x.lower() in ["true", "1"],
    required=False,
    help="Флаг для фильтрации по удаленным отчетам",
)
shift_report_filter_parser.add_argument(
    "extreme_conditions",
    # Интерпретация значения как логического
    type=lambda x: x.lower() in ["true", "1"],
    required=False,
    help="Флаг для фильтрации по удаленным отчетам",
)

shift_report_filter_parser.add_argument(
    "deleted",
    # Интерпретация значения как логического
    type=lambda x: x.lower() in ["true", "1"],
    required=False,
    help="Флаг для фильтрации по удаленным отчетам",
)
