from marshmallow import Schema, fields, validate, validates, ValidationError
from app.schemas.validators import validate_user_exists, validate_project_exists


class ShiftReportCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    user = fields.String(required=True, error_messages={
                         "required": "Field 'user' is required."}, validate=[validate_user_exists])
    date = fields.Int(required=True, error_messages={
                      "required": "Field 'date' is required."})
    project = fields.String(required=True, error_messages={
                            "required": "Field 'project' is required."}, validate=[validate_project_exists])
    signed = fields.Boolean(required=False, error_messages={
                            "required": "Field 'signed' is required."})

    @validates("date")
    def validate_date(self, value):
        """Проверяем, что дата — корректный Unix timestamp"""
        if value < 0:
            raise ValidationError(
                "Field 'date' must be a positive Unix timestamp.")


class ShiftReportEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    user = fields.String(required=False, allow_none=True,
                         validate=[validate_user_exists])
    date = fields.Int(required=False, allow_none=True)
    project = fields.String(required=False, allow_none=True, validate=[
                            validate_project_exists])
    signed = fields.Boolean(required=False, allow_none=True)


class ShiftReportFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=10, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
    user = fields.String(required=False)
    date = fields.Int(required=False)
    project = fields.String(required=False)
    deleted = fields.Boolean(required=False)
