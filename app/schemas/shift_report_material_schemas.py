from marshmallow import Schema, ValidationError, fields, pre_load, validate

from app.schemas.validators import (
    validate_shift_report_detail_exists,
    validate_shift_report_exists,
)


def validate_positive_quantity(value: float | None) -> None:
    if value is None:
        return

    if value <= 0:
        raise ValidationError("Field 'quantity' must be greater than 0.")


class ShiftReportMaterialCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    shift_report = fields.String(
        required=True,
        error_messages={"required": "Field 'shift_report' is required."},
        validate=[validate_shift_report_exists],
    )
    project_material = fields.UUID(required=True, allow_none=False)
    quantity = fields.Float(
        required=True,
        validate=[validate_positive_quantity],
        error_messages={"required": "Field 'quantity' is required."},
    )
    shift_report_detail = fields.String(
        required=False,
        allow_none=True,
        validate=[validate_shift_report_detail_exists],
    )


class ShiftReportMaterialEditSchema(Schema):
    class Meta:
        unknown = "exclude"

    shift_report = fields.String(
        required=False,
        allow_none=True,
        validate=[validate_shift_report_exists],
    )
    project_material = fields.UUID(required=False, allow_none=False)
    quantity = fields.Float(
        required=False,
        allow_none=True,
        validate=[validate_positive_quantity],
    )
    shift_report_detail = fields.String(
        required=False,
        allow_none=True,
        validate=[validate_shift_report_detail_exists],
    )


class ShiftReportMaterialFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(
        required=False,
        load_default=0,
        validate=validate.Range(min=0, error="Offset must be non-negative."),
    )
    limit = fields.Int(
        required=False,
        load_default=1000,
        validate=validate.Range(min=1, error="Limit must be at least 1."),
    )
    sort_by = fields.String(required=False)
    sort_order = fields.String(
        required=False,
        validate=validate.OneOf(
            ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."
        ),
    )
    shift_report = fields.String(required=False)
    project_material = fields.UUID(required=False)
    shift_report_detail = fields.String(required=False)

    @pre_load
    def _reject_legacy_material(self, data, **kwargs):
        if "material" in data:
            raise ValidationError(
                "Filter 'material' was removed; use 'project_material'.",
                field_name="material",
            )
        return data
