from marshmallow import Schema, fields, validate


class PlaceCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    object_id = fields.UUID(required=True)
    name = fields.String(required=True, validate=validate.Length(min=1))
    description = fields.String(required=False, allow_none=True)


class PlaceEditSchema(Schema):
    class Meta:
        unknown = "exclude"

    object_id = fields.UUID(required=False)
    name = fields.String(required=False, validate=validate.Length(min=1))
    description = fields.String(required=False, allow_none=True)
    deleted = fields.Boolean(required=False)
