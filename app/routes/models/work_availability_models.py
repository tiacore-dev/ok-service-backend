"""Swagger fields describing work availability for a shift performer."""

from flask_restx import fields

SHIFT_REPORT_PARAM_HELP = (
    "Shift report ID. When set, each item gets `available` and "
    "`unavailable_reason` for the performer of this shift"
)

availability_fields = {
    "available": fields.Boolean(
        required=False,
        description=(
            "Whether the work can be added to the shift from `shift_report`; "
            "absent or null when `shift_report` is not passed"
        ),
    ),
    "unavailable_reason": fields.String(
        required=False,
        description="Why the work is unavailable; null when it is available",
    ),
}
