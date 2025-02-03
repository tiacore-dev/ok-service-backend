from marshmallow import Schema, fields, validate


class ProjectWorkCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    work = fields.String(required=True, error_messages={
                         "required": "Field 'work' is required."})
    quantity = fields.Float(required=True, error_messages={
                            "required": "Field 'quantity' is required."})
    summ = fields.Float(required=False)  # Опциональное поле
    signed = fields.Boolean(required=True, error_messages={
                            "required": "Field 'signed' is required."})


class ProjectWorkEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    work = fields.String(required=False, allow_none=True)
    quantity = fields.Float(required=False, allow_none=True)
    summ = fields.Float(required=False, allow_none=True)  # Опциональное поле
    signed = fields.Boolean(required=False, allow_none=True)


class ProjectWorkFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=10, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
    signed = fields.Boolean(required=False)
    work = fields.String(required=False)
    min_quantity = fields.Float(required=False)
    max_quantity = fields.Float(required=False)
    min_summ = fields.Float(required=False)
    max_summ = fields.Float(required=False)
