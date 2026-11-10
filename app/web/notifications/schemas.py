from marshmallow import Schema, fields, validate


class BulkNotificationSchema(Schema):
    recipient_user_ids = fields.List(fields.UUID(), required=True, validate=validate.Length(min=1, max=100))
    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    text = fields.String(required=True, validate=validate.Length(min=1, max=4000))
    link = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=2048))
    idempotency_key = fields.String(required=True, validate=validate.Length(min=1, max=128))


class NotificationItemSchema(Schema):
    notification_id = fields.UUID(required=True)
    notification_type = fields.String(required=True)
    title = fields.String(required=True)
    text = fields.String(required=True)
    created_at = fields.Integer(required=True)
    link = fields.String(allow_none=True)
    related_entity_type = fields.String(allow_none=True)
    related_entity_id = fields.String(allow_none=True)
    viewed = fields.Boolean(required=True)
    viewed_at = fields.Integer(allow_none=True)


class AdminNotificationItemSchema(NotificationItemSchema):
    notification_recipient_id = fields.UUID(required=True)
    user_id = fields.UUID(required=True)
    browser_id = fields.UUID(allow_none=True)


class NotificationListQuerySchema(Schema):
    offset = fields.Integer(load_default=0, validate=validate.Range(min=0))
    limit = fields.Integer(load_default=50, validate=validate.Range(min=1, max=100))
