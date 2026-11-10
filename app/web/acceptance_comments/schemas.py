from marshmallow import Schema, fields, validate


class AcceptanceCommentCreateSchema(Schema):
    text = fields.String(required=True, validate=validate.Length(min=1))


class AcceptanceCommentEditSchema(AcceptanceCommentCreateSchema):
    pass


class AcceptanceCommentAttachmentSchema(Schema):
    attachment_id = fields.UUID(required=True)
    name = fields.String(required=True)
    file_size = fields.Integer(required=True)
    checksum = fields.String(required=True)
    meta = fields.Dict(required=True)
    created_at = fields.Integer(required=True)
    created_by = fields.UUID(required=True)


class AcceptanceCommentSchema(Schema):
    acceptance_comment_id = fields.UUID(required=True)
    text = fields.String(required=True)
    created_by = fields.UUID(required=True)
    author_name = fields.String(allow_none=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(allow_none=True)
    browser_id = fields.UUID(allow_none=True)
    attachments = fields.List(fields.Nested(AcceptanceCommentAttachmentSchema), required=True)


class AcceptanceCommentListSchema(Schema):
    total = fields.Integer(required=True)
    comments = fields.List(fields.Nested(AcceptanceCommentSchema), required=True)


class AcceptanceCommentListQuerySchema(Schema):
    offset = fields.Integer(load_default=0, validate=validate.Range(min=0))
    limit = fields.Integer(load_default=50, validate=validate.Range(min=1, max=100))
