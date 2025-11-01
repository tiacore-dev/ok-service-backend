from marshmallow import Schema, fields, validate, validates, validates_schema, ValidationError
from app.schemas.validators import validate_user_exists, validate_project_exists, validate_work_exists, validate_project_work_exists


class ShiftReportDetailSchema(Schema):
    """Схема для валидации деталей отчета"""
    work = fields.String(required=True, error_messages={
        "required": "Field 'work' is required."
    }, validate=[validate_work_exists])

    quantity = fields.Float(required=True, error_messages={
        "required": "Field 'quantity' is required."
    })

    summ = fields.Float(required=True, error_messages={
        "required": "Field 'summ' is required."
    })

    project_work = fields.String(required=True, error_messages={
        "required": "Field 'project_work' is required."
    }, validate=[validate_project_work_exists])


class ShiftReportCreateSchema(Schema):
    """Схема для валидации создания shift_report"""
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    user = fields.String(required=True, error_messages={
        "required": "Field 'user' is required."
    }, validate=[validate_user_exists])

    date = fields.Int(required=True, error_messages={
        "required": "Field 'date' is required."
    })
    date_start = fields.Int(required=False)
    date_end = fields.Int(required=False)

    project = fields.String(required=True, error_messages={
        "required": "Field 'project' is required."
    }, validate=[validate_project_exists])

    signed = fields.Boolean(required=False)

    night_shift = fields.Boolean(required=False)

    extreme_conditions = fields.Boolean(required=False)

    details = fields.List(fields.Nested(
        ShiftReportDetailSchema), required=False)

    @validates("date")
    def validate_date(self, value):
        """Проверяем, что дата — корректный Unix timestamp"""
        if value < 0:
            raise ValidationError(
                "Field 'date' must be a positive Unix timestamp.")

    @validates_schema
    def validate_date_range(self, data, **kwargs):
        """Убеждаемся, что временные значения заданы корректно"""
        for field_name in ["date_start", "date_end"]:
            if field_name in data and data[field_name] is not None and data[field_name] < 0:
                raise ValidationError(
                    f"Field '{field_name}' must be a positive Unix timestamp.",
                    field_name,
                )

        date_start = data.get("date_start")
        date_end = data.get("date_end")
        if date_start is not None and date_end is not None and date_end < date_start:
            raise ValidationError(
                "Field 'date_end' must be greater than or equal to 'date_start'.",
                "date_end",
            )


class ShiftReportEditSchema(Schema):
    class Meta:

        unknown = "exclude"  # Исключать лишние поля
    user = fields.String(required=False, allow_none=True,
                         validate=[validate_user_exists])
    date = fields.Int(required=False, allow_none=True)
    date_start = fields.Int(required=False, allow_none=True)
    date_end = fields.Int(required=False, allow_none=True)
    project = fields.String(required=False, allow_none=True, validate=[
        validate_project_exists])
    signed = fields.Boolean(
        required=False, allow_none=True)
    night_shift = fields.Boolean(required=False, allow_none=True)
    extreme_conditions = fields.Boolean(required=False, allow_none=True)
    deleted = fields.Boolean(required=False, allow_none=True)

    @validates_schema
    def validate_date_range(self, data, **kwargs):
        for field_name in ["date", "date_start", "date_end"]:
            if field_name in data and data[field_name] is not None and data[field_name] < 0:
                raise ValidationError(
                    f"Field '{field_name}' must be a positive Unix timestamp.",
                    field_name,
                )

        date_start = data.get("date_start")
        date_end = data.get("date_end")
        if date_start is not None and date_end is not None and date_end < date_start:
            raise ValidationError(
                "Field 'date_end' must be greater than or equal to 'date_start'.",
                "date_end",
            )


class ShiftReportFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=1000, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
    user = fields.String(required=False)
    date_from = fields.Int(required=False)
    date_to = fields.Int(required=False)
    date_start_from = fields.Int(required=False)
    date_start_to = fields.Int(required=False)
    date_end_from = fields.Int(required=False)
    date_end_to = fields.Int(required=False)
    project = fields.String(required=False)
    night_shift = fields.Boolean(required=False)
    extreme_conditions = fields.Boolean(required=False)
    deleted = fields.Boolean(required=False)
