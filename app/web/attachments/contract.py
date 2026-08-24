from flask_restx import Model, fields


attachment_view_model = Model(
    "AttachmentView",
    {
        "attachment_id": fields.String(required=True),
        "name": fields.String(required=True),
        "file_size": fields.Integer(required=True),
        "checksum": fields.String(required=True),
        "meta": fields.Raw(required=True),
        "created_at": fields.Integer(required=True),
        "created_by": fields.String(required=True),
    },
)
