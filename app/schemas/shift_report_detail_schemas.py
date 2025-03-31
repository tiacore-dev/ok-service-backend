from marshmallow import Schema, fields, validate, validates
from app.schemas.validators import validate_work_exists, validate_shift_report_exists


class ShiftReportDetailsCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    shift_report = fields.String(required=True, error_messages={
                                 "required": "Field 'shift_report' is required."}, validate=[validate_shift_report_exists])
    work = fields.String(required=True, error_messages={
                         "required": "Field 'work' is required."}, validate=[validate_work_exists])
    quantity = fields.Float(required=True, error_messages={
                            "required": "Field 'quantity' is required."})
    # summ = fields.Float(required=False)


class ShiftReportDetailsEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    shift_report = fields.String(required=False, allow_none=True, validate=[
                                 validate_shift_report_exists])
    work = fields.String(required=False, allow_none=True,
                         validate=[validate_work_exists])
    quantity = fields.Float(required=False, allow_none=True)
    # summ = fields.Float(required=False, allow_none=True)


class ShiftReportDetailsByReportsSchema(Schema):
    class Meta:
        unknown = "exclude"

    shift_report_ids = fields.List(
        fields.UUID(),
        required=False,
        allow_none=True
    )

    @validates("shift_report_ids")
    def validate_shift_report_ids_exist(self, value):
        for uuid_val in value:
            validate_shift_report_exists(str(uuid_val))


class ShiftReportDetailsFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=1000, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
    shift_report = fields.String(required=False)
    work = fields.String(required=False)
    min_quantity = fields.Float(required=False)
    max_quantity = fields.Float(required=False)
    min_summ = fields.Float(required=False)
    max_summ = fields.Float(required=False)
