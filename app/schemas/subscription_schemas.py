from marshmallow import Schema, fields, validate


class SubscriptionSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля
    # subscription_data = fields.String(required=True)
    endpoint = fields.String(required=True, error_messages={
        "required": "Field 'endpoint' is required."
    })
    keys = fields.Dict(required=True, error_messages={
        "required": "Field 'keys' is required."
    })
    # p256dh = fields.String(required=True, error_messages={
    #    "required": "Field 'p256dh' is required."
    # })
    # auth = fields.String(required=True, error_messages={
    #    "required": "Field 'auth' is required."
    # })


class SubscriptionGetSchema(Schema):
    endpoint = fields.String(required=False)
    keys = fields.Dict(required=False)
    user = fields.String(required=False)
    offset = fields.Int(required=False, missing=0, validate=validate.Range(
        min=0, error="Offset must be non-negative."))
    limit = fields.Int(required=False, missing=1000, validate=validate.Range(
        min=1, error="Limit must be at least 1."))
    sort_by = fields.String(required=False)
    sort_order = fields.String(required=False, validate=validate.OneOf(
        ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."))
