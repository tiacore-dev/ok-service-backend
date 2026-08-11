from flask_restx import Model, fields

from app.schemas.place_schemas import PlaceCreateSchema, PlaceEditSchema
from app.utils.helpers import generate_swagger_model

place_create_model = generate_swagger_model(PlaceCreateSchema(), "PlaceCreate")
place_edit_model = generate_swagger_model(PlaceEditSchema(), "PlaceEdit")
place_model = Model(
    "Place",
    {
        "place_id": fields.String(required=True),
        "object_id": fields.String(required=True),
        "name": fields.String(required=True),
        "description": fields.String(required=False, allow_none=True),
        "deleted": fields.Boolean(required=True),
    },
)
place_msg_model = Model(
    "PlaceMessage", {"msg": fields.String(required=True), "place_id": fields.String()}
)
place_response = Model(
    "PlaceResponse",
    {"msg": fields.String(required=True), "place": fields.Nested(place_model, required=True)},
)
place_all_response = Model(
    "PlaceAllResponse",
    {"msg": fields.String(required=True), "places": fields.List(fields.Nested(place_model))},
)
