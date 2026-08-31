from marshmallow import Schema, fields, validate


class WorkPlanCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    user_id = fields.String(required=False, allow_none=True)
    date = fields.Date(required=True)
    summ = fields.Decimal(required=True, as_string=False, validate=validate.Range(min=0))
    description = fields.String(required=False, allow_none=True)


class WorkPlanEditSchema(Schema):
    class Meta:
        unknown = "exclude"

    user_id = fields.String(required=False, allow_none=True)
    date = fields.Date(required=False)
    summ = fields.Decimal(required=False, validate=validate.Range(min=0))
    description = fields.String(required=False, allow_none=True)


class WorkPlanFilterSchema(Schema):
    class Meta:
        unknown = "exclude"

    offset = fields.Int(load_default=0, validate=validate.Range(min=0))
    limit = fields.Int(load_default=1000, validate=validate.Range(min=1))
    sort_by = fields.String(load_default="date")
    sort_order = fields.String(load_default="asc", validate=validate.OneOf(["asc", "desc"]))
    year = fields.Int(required=False, validate=validate.Range(min=1))
    user_id = fields.String(required=False, allow_none=True)
    user_id_is_null = fields.Boolean(required=False, allow_none=True)
    deleted = fields.Boolean(load_default=False)
