from marshmallow import Schema, ValidationError, fields, validate

from app.domain.work_prices import validate_work_price_value
from app.schemas.validators import validate_work_exists


def validate_price(value):
    """Payment amount `>= 0`, or `-1` when the work is unavailable for the category."""
    try:
        validate_work_price_value(value)
    except ValueError as error:
        raise ValidationError(str(error)) from error


class WorkPriceCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    work = fields.String(required=True, error_messages={
                         "required": "Field 'work' is required."}, validate=[validate_work_exists])
    category = fields.Int(required=True, error_messages={
                          "required": "Field 'category' is required."}, validate=validate.OneOf([0, 1, 2, 3, 4]))
    price = fields.Float(required=True, error_messages={
                         "required": "Field 'price' is required."},
                         validate=validate_price)


class WorkPriceEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    work = fields.String(required=False, allow_none=True,
                         validate=[validate_work_exists])
    category = fields.Int(required=False, allow_none=False,
                          validate=validate.OneOf([0, 1, 2, 3, 4]))
    price = fields.Float(required=False, allow_none=False, validate=validate_price)
    deleted = fields.Boolean(required=False, allow_none=True)


class WorkPriceFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, load_default=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, load_default=1000, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    work = fields.String(required=False)
    category = fields.Int(required=False)
    price = fields.Float(required=False)
    created_by = fields.String(required=False)
    created_at = fields.Int(required=False)
    deleted = fields.Boolean(required=False)
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
