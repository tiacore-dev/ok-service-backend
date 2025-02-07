from marshmallow import Schema, fields, validate
from app.schemas.validators import validate_user_exists, validate_object_exists


class ProjectCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    name = fields.String(required=True, error_messages={
                         "required": "Field 'name' is required."})
    object = fields.String(required=True, error_messages={
                           "required": "Field 'object' is required."}, validate=[validate_object_exists])
    project_leader = fields.String(
        required=False, validate=[validate_user_exists])
    night_shift_available = fields.Boolean(required=False)
    extreme_conditions_available = fields.Boolean(required=False)


class ProjectEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    name = fields.String(required=False, allow_none=True)
    object = fields.String(required=False, allow_none=True,
                           validate=[validate_user_exists])
    project_leader = fields.String(
        required=False, allow_none=True, validate=[validate_user_exists])
    night_shift_available = fields.Boolean(required=False)
    extreme_conditions_available = fields.Boolean(required=False)


class ProjectFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=10, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
    object = fields.String(required=False)
    project_leader = fields.String(required=False)
    name = fields.String(required=False)
    night_shift_available = fields.Boolean(required=False)
    extreme_conditions_available = fields.Boolean(required=False)
    deleted = fields.Boolean(required=False)
