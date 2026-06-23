from marshmallow import Schema, fields, validate


class ApiKeyGenerateSchema(Schema):
    class Meta:
        unknown = "exclude"

    name = fields.String(
        required=True, error_messages={"required": "Field 'name' is required."}
    )
    expires_at = fields.Int(
        required=True, error_messages={"required": "Field 'expires_at' is required."}
    )


class ApiKeyFilterSchema(Schema):
    class Meta:
        unknown = "exclude"

    offset = fields.Int(
        required=False,
        load_default=0,
        validate=validate.Range(min=0, error="Offset must be non-negative."),
    )
    limit = fields.Int(
        required=False,
        load_default=1000,
        validate=validate.Range(min=1, error="Limit must be at least 1."),
    )
    sort_by = fields.String(required=False)
    sort_order = fields.String(
        required=False,
        validate=validate.OneOf(
            ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."
        ),
    )
