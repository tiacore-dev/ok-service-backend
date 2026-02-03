from flask_restx import Model, fields, reqparse

from app.schemas.shift_report_material_schemas import ShiftReportMaterialCreateSchema
from app.utils.helpers import generate_swagger_model

shift_report_material_create_model = generate_swagger_model(
    ShiftReportMaterialCreateSchema(), "ShiftReportMaterialCreate"
)

shift_report_material_model = Model(
    "ShiftReportMaterial",
    {
        "shift_report_material_id": fields.String(
            required=True, description="ID of the shift report material"
        ),
        "shift_report": fields.String(required=True, description="Shift report ID"),
        "material": fields.String(required=True, description="Material ID"),
        "quantity": fields.Float(required=True, description="Quantity of material"),
        "shift_report_detail": fields.String(
            required=False, description="Shift report detail ID (optional)"
        ),
        "created_at": fields.Integer(required=True, description="Created at timestamp"),
        "created_by": fields.String(required=True, description="Creator of record"),
    },
)

shift_report_material_msg_model = Model(
    "ShiftReportMaterialMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
        "shift_report_material_id": fields.String(
            description="ID of shift report material"
        ),
    },
)

shift_report_material_response = Model(
    "ShiftReportMaterialResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "shift_report_material": fields.Nested(
            shift_report_material_model, required=True
        ),
    },
)

shift_report_material_all_response = Model(
    "ShiftReportMaterialAllResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "shift_report_materials": fields.List(
            fields.Nested(shift_report_material_model),
            description="List of shift report materials",
        ),
    },
)

shift_report_material_filter_parser = reqparse.RequestParser()
shift_report_material_filter_parser.add_argument(
    "offset", type=int, default=0, help="Offset for pagination"
)
shift_report_material_filter_parser.add_argument(
    "limit", type=int, default=10, help="Limit for pagination"
)
shift_report_material_filter_parser.add_argument(
    "shift_report", type=str, required=False, help="Filter by shift report ID"
)
shift_report_material_filter_parser.add_argument(
    "material", type=str, required=False, help="Filter by material ID"
)
shift_report_material_filter_parser.add_argument(
    "shift_report_detail",
    type=str,
    required=False,
    help="Filter by shift report detail ID",
)
shift_report_material_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Field for sorting"
)
shift_report_material_filter_parser.add_argument(
    "sort_order", type=str, required=False, choices=["asc", "desc"], help="Sort order"
)
