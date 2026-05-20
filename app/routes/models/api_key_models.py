from flask_restx import Model, fields, reqparse

from app.schemas.api_key_schemas import ApiKeyGenerateSchema
from app.utils.helpers import generate_swagger_model

api_key_generate_model = generate_swagger_model(ApiKeyGenerateSchema(), "ApiKeyGenerate")

api_key_model = Model(
    "ApiKey",
    {
        "api_key_id": fields.String(required=True, description="ID API key"),
        "name": fields.String(required=True, description="Name API key"),
        "expires_at": fields.Integer(required=True, description="Expire timestamp"),
        "created_at": fields.Integer(required=True, description="Created timestamp"),
    },
)

api_key_generate_response = Model(
    "ApiKeyGenerateResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "api_key_id": fields.String(required=True, description="ID API key"),
        "token": fields.String(required=True, description="Generated token"),
    },
)

api_key_msg_model = Model(
    "ApiKeyMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
        "api_key_id": fields.String(required=False, description="ID API key"),
    },
)

api_key_response = Model(
    "ApiKeyResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "api_key": fields.Nested(api_key_model, required=True, description="API key"),
    },
)

api_key_all_response = Model(
    "ApiKeyAllResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "api_keys": fields.List(fields.Nested(api_key_model), description="List of API keys"),
    },
)

api_key_filter_parser = reqparse.RequestParser()
api_key_filter_parser.add_argument(
    "offset", type=int, required=False, default=0, help="Offset for pagination"
)
api_key_filter_parser.add_argument(
    "limit", type=int, required=False, default=10, help="Limit for pagination"
)
api_key_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Field for sorting"
)
api_key_filter_parser.add_argument(
    "sort_order",
    type=str,
    required=False,
    choices=["asc", "desc"],
    help="Sort order",
)
