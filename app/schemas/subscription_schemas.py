from marshmallow import Schema, fields


class SubscriptionSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля
    # subscription_data = fields.String(required=True)
    endpoint = fields.String(required=True, error_messages={
        "required": "Field 'endpoint' is required."
    })
    p256dh = fields.String(required=True, error_messages={
        "required": "Field 'p256dh' is required."
    })
    auth = fields.String(required=True, error_messages={
        "required": "Field 'auth' is required."
    })
