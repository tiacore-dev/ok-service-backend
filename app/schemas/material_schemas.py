from marshmallow import Schema, fields, validate


class MaterialCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    name = fields.String(
        required=True, error_messages={"required": "Field 'name' is required."}
    )
    measurement_unit = fields.String(required=False, allow_none=True)


class MaterialEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    name = fields.String(required=False, allow_none=True)
    measurement_unit = fields.String(required=False, allow_none=True)
    deleted = fields.Boolean(required=False, allow_none=True)


class MaterialFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

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
    name = fields.String(required=False)
    measurement_unit = fields.String(required=False)
    deleted = fields.Boolean(required=False)
    sort_by = fields.String(required=False)
    sort_order = fields.String(
        required=False,
        validate=validate.OneOf(
            ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."
        ),
    )
