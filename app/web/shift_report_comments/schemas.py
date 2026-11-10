from marshmallow import Schema, fields, validate


class ShiftReportCommentCreateSchema(Schema):
    text = fields.String(required=True, validate=validate.Length(min=1))


class ShiftReportCommentEditSchema(ShiftReportCommentCreateSchema):
    pass


class ShiftReportCommentAttachmentSchema(Schema):
    attachment_id = fields.UUID(required=True)
    name = fields.String(required=True)
    file_size = fields.Integer(required=True)
    checksum = fields.String(required=True)
    meta = fields.Dict(required=True)
    created_at = fields.Integer(required=True)
    created_by = fields.UUID(required=True)


class ShiftReportCommentSchema(Schema):
    shift_report_comment_id = fields.UUID(required=True)
    text = fields.String(required=True)
    created_by = fields.UUID(required=True)
    author_name = fields.String(allow_none=True)
    created_at = fields.Integer(required=True)
    updated_at = fields.Integer(allow_none=True)
    browser_id = fields.UUID(allow_none=True)
    attachments = fields.List(fields.Nested(ShiftReportCommentAttachmentSchema), required=True)


class ShiftReportCommentListSchema(Schema):
    total = fields.Integer(required=True)
    comments = fields.List(fields.Nested(ShiftReportCommentSchema), required=True)


class ShiftReportCommentListQuerySchema(Schema):
    offset = fields.Integer(load_default=0, validate=validate.Range(min=0))
    limit = fields.Integer(load_default=50, validate=validate.Range(min=1, max=100))
