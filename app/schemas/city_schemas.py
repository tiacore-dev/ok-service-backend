from marshmallow import Schema, fields, validate


class CityCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(
        required=True,
        error_messages={"required": "Field 'name' is required."},
    )


class CityEditSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(required=False, allow_none=True)
    deleted = fields.Boolean(required=False, allow_none=True)


class CityFilterSchema(Schema):
    class Meta:
        unknown = "exclude"

    offset = fields.Int(
        required=False,
        missing=0,
        validate=validate.Range(min=0, error="Offset must be non-negative."),
    )
    limit = fields.Int(
        required=False,
        missing=1000,
        validate=validate.Range(min=1, error="Limit must be at least 1."),
    )
    sort_by = fields.String(required=False)
    sort_order = fields.String(
        required=False,
        validate=validate.OneOf(
            ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."
        ),
    )
    name = fields.String(required=False)
    deleted = fields.Boolean(required=False)
