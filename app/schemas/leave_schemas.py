from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from app.database.models.leaves import AbsenceReason
from app.schemas.validators import (
    validate_leave_exists,
    validate_user_exists,
)

ABSENCE_REASON_CHOICES = [reason.value for reason in AbsenceReason]


class LeaveCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    start_date = fields.Int(
        required=True, error_messages={"required": "Field 'start_date' is required."}
    )
    end_date = fields.Int(
        required=True, error_messages={"required": "Field 'end_date' is required."}
    )
    reason = fields.String(
        required=True,
        validate=validate.OneOf(ABSENCE_REASON_CHOICES),
        error_messages={"required": "Field 'reason' is required."},
    )
    user = fields.String(
        required=True,
        validate=[validate_user_exists],
        error_messages={"required": "Field 'user' is required."},
    )
    responsible = fields.String(
        required=True,
        validate=[validate_user_exists],
        error_messages={"required": "Field 'responsible' is required."},
    )
    comment = fields.String(required=False, allow_none=True)

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data["start_date"] > data["end_date"]:
            raise ValidationError(
                "'start_date' must be less than or equal to 'end_date'", "start_date"
            )


class LeaveEditSchema(Schema):
    class Meta:
        unknown = "exclude"

    start_date = fields.Int(required=False, allow_none=True)
    end_date = fields.Int(required=False, allow_none=True)
    reason = fields.String(
        required=False, allow_none=True, validate=validate.OneOf(ABSENCE_REASON_CHOICES)
    )
    user = fields.String(
        required=False, allow_none=True, validate=[validate_user_exists]
    )
    responsible = fields.String(
        required=False, allow_none=True, validate=[validate_user_exists]
    )
    comment = fields.String(required=False, allow_none=True)
    updated_by = fields.String(
        required=False, allow_none=True, validate=[validate_user_exists]
    )

    @validates_schema
    def validate_dates(self, data, **kwargs):
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValidationError(
                "'start_date' must be less than or equal to 'end_date'", "start_date"
            )


class LeaveFilterSchema(Schema):
    class Meta:
        unknown = "exclude"

    offset = fields.Int(required=False, missing=0)
    limit = fields.Int(required=False, missing=1000)
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(["asc", "desc"]))
    user = fields.String(required=False)
    responsible = fields.String(required=False)
    reason = fields.String(
        required=False, validate=validate.OneOf(ABSENCE_REASON_CHOICES)
    )
    date_from = fields.Int(required=False)
    date_to = fields.Int(required=False)
    deleted = fields.Boolean(required=False)


class LeaveIdSchema(Schema):
    leave_id = fields.String(required=True, validate=[validate_leave_exists])
