import math

from marshmallow import Schema, ValidationError, fields, validate


def _finite(value: float) -> None:
    if not math.isfinite(value):
        raise ValidationError("Must be a finite number.")


class ShiftStandardCreateSchema(Schema):
    category = fields.Integer(required=True)
    standard = fields.Float(
        required=True,
        allow_nan=False,
        validate=[validate.Range(min=0, min_inclusive=False), _finite],
    )
    notification_text = fields.String(required=False, allow_none=True)


class ShiftStandardEditSchema(Schema):
    category = fields.Integer(required=False)
    standard = fields.Float(
        required=False,
        allow_nan=False,
        validate=[validate.Range(min=0, min_inclusive=False), _finite],
    )
    notification_text = fields.String(required=False, allow_none=True)


class ShiftStandardFilterSchema(Schema):
    offset = fields.Integer(load_default=0, validate=validate.Range(min=0))
    limit = fields.Integer(load_default=1000, validate=validate.Range(min=1))
    category = fields.Integer(required=False)
