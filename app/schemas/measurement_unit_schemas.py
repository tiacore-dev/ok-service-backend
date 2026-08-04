from marshmallow import Schema, fields, validate


class MeasurementUnitCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1))


class MeasurementUnitEditSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1))


class MeasurementUnitFilterSchema(Schema):
    offset = fields.Int(load_default=0, validate=validate.Range(min=0))
    limit = fields.Int(load_default=1000, validate=validate.Range(min=1))
    name = fields.String(required=False)
