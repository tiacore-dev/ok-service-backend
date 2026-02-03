from uuid import UUID

from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from app.schemas.validators import (
    validate_material_exists,
    validate_shift_report_detail_exists,
    validate_shift_report_exists,
)


def _validate_quantity_for_material(material_id_str, quantity):
    if not material_id_str or quantity is None:
        return

    try:
        material_id = UUID(material_id_str)
    except ValueError:
        return

    from app.database.managers.materials_manager import MaterialsManager

    db = MaterialsManager()
    material = db.get_by_id(material_id)
    if not material or not material.get("measurement_unit"):
        return

    unit = str(material.get("measurement_unit")).strip().lower()
    if unit == "шт.":
        rounded = int(float(quantity))
        if rounded <= 0:
            raise ValidationError(
                "Field 'quantity' must be a positive integer for unit 'шт.'.",
                "quantity",
            )
        return rounded

    return None


class ShiftReportMaterialCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    shift_report = fields.String(
        required=True,
        error_messages={"required": "Field 'shift_report' is required."},
        validate=[validate_shift_report_exists],
    )
    material = fields.String(
        required=True,
        error_messages={"required": "Field 'material' is required."},
        validate=[validate_material_exists],
    )
    quantity = fields.Float(
        required=True, error_messages={"required": "Field 'quantity' is required."}
    )
    shift_report_detail = fields.String(
        required=False, allow_none=True, validate=[validate_shift_report_detail_exists]
    )

    @validates_schema
    def validate_quantity(self, data, **kwargs):
        adjusted = _validate_quantity_for_material(
            data.get("material"), data.get("quantity")
        )
        if adjusted is not None:
            data["quantity"] = adjusted


class ShiftReportMaterialEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    shift_report = fields.String(
        required=False, allow_none=True, validate=[validate_shift_report_exists]
    )
    material = fields.String(
        required=False, allow_none=True, validate=[validate_material_exists]
    )
    quantity = fields.Float(required=False, allow_none=True)
    shift_report_detail = fields.String(
        required=False, allow_none=True, validate=[validate_shift_report_detail_exists]
    )

    @validates_schema
    def validate_quantity(self, data, **kwargs):
        adjusted = _validate_quantity_for_material(
            data.get("material"), data.get("quantity")
        )
        if adjusted is not None:
            data["quantity"] = adjusted


class ShiftReportMaterialFilterSchema(Schema):
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
    shift_report = fields.String(required=False)
    material = fields.String(required=False)
    shift_report_detail = fields.String(required=False)
