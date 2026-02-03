from marshmallow import Schema, fields, validate

from app.schemas.validators import validate_material_exists, validate_work_exists


class WorkMaterialRelationCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    work = fields.String(
        required=True,
        error_messages={"required": "Field 'work' is required."},
        validate=[validate_work_exists],
    )
    material = fields.String(
        required=True,
        error_messages={"required": "Field 'material' is required."},
        validate=[validate_material_exists],
    )
    quantity = fields.Float(
        required=True, error_messages={"required": "Field 'quantity' is required."}
    )


class WorkMaterialRelationEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    work = fields.String(required=False, allow_none=True, validate=[validate_work_exists])
    material = fields.String(
        required=False, allow_none=True, validate=[validate_material_exists]
    )
    quantity = fields.Float(required=False, allow_none=True)


class WorkMaterialRelationFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(
        required=False,
        missing=0,
        validate=validate.Range(min=0, error="Offset must be non-negative."),
    )
    limit = fields.Int(
        required=False,
        missing=1000,
        validate=validate.Range(min=1, error="Limit must be at least 1."),
    )
    sort_by = fields.String(required=False)
    sort_order = fields.String(
        required=False,
        validate=validate.OneOf(
            ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."
        ),
    )
    work = fields.String(required=False)
    material = fields.String(required=False)
