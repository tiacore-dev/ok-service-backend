from marshmallow import Schema, fields, validate
from app.schemas.validators import validate_role_exists


class UserCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    login = fields.String(required=True, error_messages={
                          "required": "Field 'login' is required."})
    password = fields.String(required=True, error_messages={
                             "required": "Field 'password' is required."})
    name = fields.String(required=True, error_messages={
                         "required": "Field 'name' is required."})
    role = fields.String(required=True, error_messages={
                         "required": "Field 'role' is required."}, validate=[validate_role_exists])
    category = fields.Int(required=False, validate=validate.OneOf(
        [0, 1, 2, 3, 4]))  # Опциональное поле


class UserEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    login = fields.String(required=False, allow_none=True)
    password = fields.String(required=False, allow_none=True)
    name = fields.String(vrequired=False, allow_none=True)
    role = fields.String(required=False, allow_none=True,
                         validate=[validate_role_exists])
    category = fields.Int(required=False, allow_none=True, validate=validate.OneOf(
        [0, 1, 2, 3, 4]))  # Опциональное поле


class UserFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=1000, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
    login = fields.String(required=False)
    name = fields.String(required=False)
    role = fields.String(required=False)
    category = fields.Int(required=False)
    deleted = fields.Boolean(required=False)
