from marshmallow import Schema, fields, validate

from app.schemas.validators import validate_work_exists


class WorkAcceptanceRelationCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    acceptance_id = fields.String(required=True)
    work_id = fields.String(required=True, validate=validate_work_exists)
    quantity = fields.Decimal(required=True, as_string=False, validate=validate.Range(min=0, min_inclusive=False))


class WorkAcceptanceRelationEditSchema(Schema):
    class Meta:
        unknown = "exclude"

    acceptance_id = fields.String(required=False, allow_none=True)
    work_id = fields.String(required=False, allow_none=True, validate=validate_work_exists)
    quantity = fields.Decimal(required=False, allow_none=True, as_string=False, validate=validate.Range(min=0, min_inclusive=False))


class WorkAcceptanceRelationFilterSchema(Schema):
    class Meta:
        unknown = "exclude"

    offset = fields.Int(load_default=0, validate=validate.Range(min=0))
    limit = fields.Int(load_default=1000, validate=validate.Range(min=1))
    acceptance_id = fields.String(required=False)
    work_id = fields.String(required=False)


class WorkAcceptanceRelationBulkWorkSchema(Schema):
    class Meta:
        unknown = "exclude"

    work_id = fields.UUID(required=True)
    quantity = fields.Decimal(
        required=True,
        as_string=False,
        validate=validate.Range(min=0, min_inclusive=False),
    )


class WorkAcceptanceRelationBulkCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    acceptance_id = fields.UUID(required=True)
    works = fields.List(
        fields.Nested(WorkAcceptanceRelationBulkWorkSchema),
        required=True,
        validate=validate.Length(min=1),
    )


class WorkAcceptanceRelationBulkDeleteSchema(Schema):
    class Meta:
        unknown = "exclude"

    relation_ids = fields.List(
        fields.UUID,
        required=True,
        validate=validate.Length(min=1),
    )
