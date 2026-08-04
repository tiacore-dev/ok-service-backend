from flask_restx import Model, fields, reqparse

from app.schemas.position_schemas import PositionCreateSchema, PositionEditSchema
from app.utils.helpers import generate_swagger_model

position_create_model = generate_swagger_model(PositionCreateSchema(), "PositionCreate")
position_edit_model = generate_swagger_model(PositionEditSchema(), "PositionEdit")

position_model = Model(
    "Position",
    {
        "position_id": fields.String(required=True, description="ID of position"),
        "name": fields.String(required=True, description="Position name"),
        "created_by": fields.String(required=False, description="Creator of position"),
        "created_at": fields.Integer(
            required=True, description="Unix epoch milliseconds: position creation time"
        ),
    },
)

position_msg_model = Model(
    "PositionMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
        "position_id": fields.String(description="ID of position"),
    },
)

position_response = Model(
    "PositionResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "position": fields.Nested(position_model, required=True),
    },
)

position_all_response = Model(
    "PositionAllResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "positions": fields.List(
            fields.Nested(position_model), description="List of positions"
        ),
    },
)

position_filter_parser = reqparse.RequestParser()
position_filter_parser.add_argument(
    "offset", type=int, required=False, default=0, help="Offset for pagination"
)
position_filter_parser.add_argument(
    "limit", type=int, required=False, default=1000, help="Limit for pagination"
)
position_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Field for sorting"
)
position_filter_parser.add_argument(
    "sort_order", type=str, required=False, choices=["asc", "desc"], help="Sort order"
)
position_filter_parser.add_argument(
    "name", type=str, required=False, help="Filter by position name"
)
