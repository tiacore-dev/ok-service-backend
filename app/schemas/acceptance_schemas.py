from marshmallow import Schema, fields, validate

from app.schemas.validators import validate_project_exists


ACCEPTANCE_STATUSES = ["presented", "violations_found", "accepted_on_site", "documents_signed"]


class AcceptanceCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    date = fields.Integer(required=True, validate=validate.Range(min=0))
    project_id = fields.String(required=True, validate=validate_project_exists)
    status = fields.String(required=True, validate=validate.OneOf(ACCEPTANCE_STATUSES))
    comment = fields.String(required=False, allow_none=True)


class AcceptanceEditSchema(Schema):
    class Meta:
        unknown = "exclude"

    date = fields.Integer(required=False, allow_none=True, validate=validate.Range(min=0))
    project_id = fields.String(required=False, allow_none=True, validate=validate_project_exists)
    status = fields.String(required=False, allow_none=True, validate=validate.OneOf(ACCEPTANCE_STATUSES))
    comment = fields.String(required=False, allow_none=True)


class AcceptanceFilterSchema(Schema):
    class Meta:
        unknown = "exclude"

    offset = fields.Int(load_default=0, validate=validate.Range(min=0))
    limit = fields.Int(load_default=1000, validate=validate.Range(min=1))
    project_id = fields.String(required=False)
    status = fields.String(required=False, validate=validate.OneOf(ACCEPTANCE_STATUSES))


class AcceptanceHistoryFilterSchema(Schema):
    class Meta:
        unknown = "exclude"

    offset = fields.Int(load_default=0, validate=validate.Range(min=0))
    limit = fields.Int(load_default=1000, validate=validate.Range(min=1))
