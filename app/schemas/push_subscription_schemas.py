from marshmallow import Schema, fields


class PushSubscriptionSchema(Schema):
    class Meta:
        unknown = "exclude"

    platform = fields.String(required=True)
    token = fields.String(required=True)
