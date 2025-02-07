from marshmallow import Schema, fields, validate
from app.schemas.validators import validate_work_exists, validate_project_exists


class ProjectScheduleCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    work = fields.String(required=True, error_messages={
                         "required": "Field 'work' is required."}, validate=[validate_work_exists])
    project = fields.String(required=True, error_messages={
        "required": "Field 'project' is required."}, validate=[validate_project_exists])
    quantity = fields.Float(required=True, error_messages={
                            "required": "Field 'quantity' is required."})
    date = fields.Int(required=False)  # Опциональное поле


class ProjectScheduleEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    work = fields.String(required=False, allow_none=True,
                         validate=[validate_work_exists])
    project = fields.String(required=False,  validate=[
                            validate_project_exists])
    quantity = fields.Float(required=False, allow_none=True)
    date = fields.Int(required=False, allow_none=True)  # Опциональное поле


class ProjectScheduleFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=10, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
    work = fields.String(required=False)
    project = fields.String(required=False)
    date = fields.Int(required=False)
