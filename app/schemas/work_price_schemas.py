from marshmallow import Schema, fields, validate


class WorkPriceCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    work = fields.String(required=True, error_messages={
                         "required": "Field 'work' is required."})
    name = fields.String(required=True, error_messages={
                         "required": "Field 'name' is required."})
    category = fields.Int(required=True, error_messages={
                          "required": "Field 'category' is required."})
    price = fields.Float(required=True, error_messages={
                         "required": "Field 'price' is required."})


class WorkPriceFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=10, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    name = fields.String(required=False)
    deleted = fields.Boolean(required=False)
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
