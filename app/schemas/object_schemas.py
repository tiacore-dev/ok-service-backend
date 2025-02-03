from marshmallow import Schema, fields


class ObjectCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Игнорировать лишние поля
    name = fields.String(required=True, error_messages={
                         "required": "Field 'name' is required."})
    address = fields.String(required=False)
    description = fields.String(required=False)
    status = fields.String(required=False)


class ObjectEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Игнорировать лишние поля
    name = fields.String(required=False, allow_none=True)
    address = fields.String(required=False, allow_none=True)
    description = fields.String(required=False, allow_none=True)
    status = fields.String(required=False, allow_none=True)


class ObjectFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Игнорировать лишние поля
    offset = fields.Int(required=False, missing=0)
    limit = fields.Int(required=False, missing=10)
    sort_by = fields.String(required=False)
    sort_order = fields.String(
        required=False, validate=lambda x: x in ["asc", "desc"])
    address = fields.String(required=False)
    status = fields.String(required=False)
    name = fields.String(required=False)
    deleted = fields.Boolean(required=False)
