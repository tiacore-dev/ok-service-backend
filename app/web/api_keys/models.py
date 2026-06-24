from flask_restx import Model, fields, reqparse

from app.schemas.api_key_schemas import ApiKeyGenerateSchema
from app.schemas.key_permission_type_relation_schemas import (
    KeyPermissionTypeRelationBulkDeleteSchema,
    KeyPermissionTypeRelationBulkCreateSchema,
    KeyPermissionTypeRelationCreateSchema,
)
from app.utils.helpers import generate_swagger_model

api_key_generate_model = generate_swagger_model(ApiKeyGenerateSchema(), "ApiKeyGenerate")
key_permission_relation_create_model = generate_swagger_model(
    KeyPermissionTypeRelationCreateSchema(), "KeyPermissionTypeRelationCreate"
)
key_permission_relation_bulk_create_model = generate_swagger_model(
    KeyPermissionTypeRelationBulkCreateSchema(), "KeyPermissionTypeRelationBulkCreate"
)
key_permission_relation_bulk_delete_model = generate_swagger_model(
    KeyPermissionTypeRelationBulkDeleteSchema(), "KeyPermissionTypeRelationBulkDelete"
)

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
        "api_keys": fields.List(
            fields.Nested(api_key_model), description="List of API keys"
        ),
    },
)

permission_type_model = Model(
    "PermissionType",
    {
        "permission_type_id": fields.String(required=True, description="Permission type ID"),
        "code": fields.String(required=True, description="Permission code"),
        "description": fields.String(required=False, description="Endpoint description"),
    },
)

permission_type_all_response = Model(
    "PermissionTypeAllResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "permission_types": fields.List(
            fields.Nested(permission_type_model), description="List of permission types"
        ),
    },
)

key_permission_relation_model = Model(
    "KeyPermissionTypeRelation",
    {
        "id": fields.String(required=True, description="Relation ID"),
        "api_key_id": fields.String(required=True, description="API key ID"),
        "permission_type_id": fields.String(
            required=True, description="Permission type ID"
        ),
    },
)

key_permission_relation_response = Model(
    "KeyPermissionTypeRelationResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "relation": fields.Nested(
            key_permission_relation_model, description="Relation data"
        ),
    },
)

key_permission_relation_msg_model = Model(
    "KeyPermissionTypeRelationMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
        "id": fields.String(required=False, description="Relation ID"),
    },
)

key_permission_relation_all_response = Model(
    "KeyPermissionTypeRelationAllResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "relations": fields.List(
            fields.Nested(key_permission_relation_model), description="List of relations"
        ),
    },
)

key_permission_relation_bulk_response = Model(
    "KeyPermissionTypeRelationBulkResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "relations": fields.List(
            fields.Nested(key_permission_relation_model), description="Created relations"
        ),
    },
)

key_permission_relation_bulk_delete_response = Model(
    "KeyPermissionTypeRelationBulkDeleteResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "deleted_ids": fields.List(fields.String, description="Deleted relation IDs"),
        "deleted_count": fields.Integer(
            required=True, description="Deleted relations count"
        ),
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

permission_type_filter_parser = reqparse.RequestParser()
permission_type_filter_parser.add_argument(
    "offset", type=int, required=False, default=0, help="Offset for pagination"
)
permission_type_filter_parser.add_argument(
    "limit", type=int, required=False, default=1000, help="Limit for pagination"
)
permission_type_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Field for sorting"
)
permission_type_filter_parser.add_argument(
    "sort_order",
    type=str,
    required=False,
    choices=["asc", "desc"],
    help="Sort order",
)

key_permission_relation_filter_parser = reqparse.RequestParser()
key_permission_relation_filter_parser.add_argument(
    "offset", type=int, required=False, default=0, help="Offset for pagination"
)
key_permission_relation_filter_parser.add_argument(
    "limit", type=int, required=False, default=1000, help="Limit for pagination"
)
key_permission_relation_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Field for sorting"
)
key_permission_relation_filter_parser.add_argument(
    "sort_order",
    type=str,
    required=False,
    choices=["asc", "desc"],
    help="Sort order",
)
key_permission_relation_filter_parser.add_argument(
    "api_key_id", type=str, required=False, help="Filter by API key ID"
)
key_permission_relation_filter_parser.add_argument(
    "permission_type_id", type=str, required=False, help="Filter by permission type ID"
)
