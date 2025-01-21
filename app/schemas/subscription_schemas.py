from marshmallow import Schema, fields


class SubscriptionSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля
    subscription_data = fields.String(required=True)
