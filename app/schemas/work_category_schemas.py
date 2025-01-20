from marshmallow import Schema, fields, validate


class WorkCategoryCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    name = fields.String(required=True, error_messages={
                         "required": "Field 'name' is required."})


class WorkCategoryEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    name = fields.String(required=False, allow_none=True)


class WorkCategoryFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=10, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
    name = fields.String(required=False)
    deleted = fields.Boolean(required=False)
