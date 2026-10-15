from flask_restx import Model, fields, reqparse

from app.schemas.shift_standard_schemas import ShiftStandardCreateSchema, ShiftStandardEditSchema
from app.utils.helpers import generate_swagger_model

shift_standard_create_model = generate_swagger_model(ShiftStandardCreateSchema(), "ShiftStandardCreate")
shift_standard_edit_model = generate_swagger_model(ShiftStandardEditSchema(), "ShiftStandardEdit")
shift_standard_model = Model("ShiftStandard", {
    "shift_standard_id": fields.String(required=True),
    "category": fields.Integer(required=True),
    "standard": fields.Float(required=True),
    "notification_text": fields.String(required=False, allow_none=True),
    "created_at": fields.Integer(required=True),
    "created_by": fields.String(required=True),
})
shift_standard_msg_model = Model("ShiftStandardMessage", {
    "msg": fields.String(required=True), "shift_standard_id": fields.String()
})
shift_standard_response = Model("ShiftStandardResponse", {
    "msg": fields.String(required=True), "shift_standard": fields.Nested(shift_standard_model, required=True)
})
shift_standard_all_response = Model("ShiftStandardAllResponse", {
    "msg": fields.String(required=True), "shift_standards": fields.List(fields.Nested(shift_standard_model))
})
shift_standard_filter_parser = reqparse.RequestParser()
shift_standard_filter_parser.add_argument("offset", type=int, default=0)
shift_standard_filter_parser.add_argument("limit", type=int, default=1000)
shift_standard_filter_parser.add_argument("category", type=int)
