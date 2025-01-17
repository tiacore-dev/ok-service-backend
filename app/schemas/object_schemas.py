from marshmallow import Schema, fields


class ObjectCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Игнорировать лишние поля
    name = fields.String(required=True, error_messages={
                         "required": "Field 'name' is required."})
    address = fields.String()
    description = fields.String()
    status = fields.String()


class ObjectFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Игнорировать лишние поля
    offset = fields.Int(required=False, missing=0)
    limit = fields.Int(required=False, missing=10)
    sort_by = fields.String(required=False)
    sort_order = fields.String(
        required=False, validate=lambda x: x in ["asc", "desc"])
    name = fields.String(required=False)
    deleted = fields.Boolean(required=False)
