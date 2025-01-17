from marshmallow import Schema, fields, validate


class ShiftReportDetailsCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    shift_report = fields.String(required=True, error_messages={
                                 "required": "Field 'shift_report' is required."})
    work = fields.String(required=True, error_messages={
                         "required": "Field 'work' is required."})
    quantity = fields.Float(required=True, error_messages={
                            "required": "Field 'quantity' is required."})
    summ = fields.Float(required=True, error_messages={
                        "required": "Field 'summ' is required."})


class ShiftReportDetailsFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=10, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
    shift_report = fields.String(required=False)
    work = fields.String(required=False)
