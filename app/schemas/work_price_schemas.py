from marshmallow import Schema, fields, validate
from app.schemas.validators import validate_work_exists


class WorkPriceCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    work = fields.String(required=True, error_messages={
                         "required": "Field 'work' is required."}, validate=[validate_work_exists])
    category = fields.Int(required=True, error_messages={
                          "required": "Field 'category' is required."})
    price = fields.Float(required=True, error_messages={
                         "required": "Field 'price' is required."})


class WorkPriceEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    work = fields.String(required=False, allow_none=True,
                         validate=[validate_work_exists])
    category = fields.Int(required=False, allow_none=True)
    price = fields.Float(required=False, allow_none=True)


class WorkPriceFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=10, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    work = fields.String(required=False)
    category = fields.Int(required=False)
    price = fields.Float(required=False)
    deleted = fields.Boolean(required=False)
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
