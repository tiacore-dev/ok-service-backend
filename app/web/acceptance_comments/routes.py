from io import BytesIO

from flask import request, send_file
from flask_restx import Namespace, Resource, fields

from app.decorators import api_key_or_jwt_required
from app.use_cases.attachments import UploadFile
from app.use_cases.report_comments.service import CommentError, ReportCommentService
from app.web.utils.report_comments import (
    browser_id,
    comment_actor,
    comment_attachment_parser,
    load_pagination_query,
    load_payload,
    map_comment_error,
    parse_uuid,
    set_browser_id_cookie,
)

from .schemas import (
    AcceptanceCommentCreateSchema,
    AcceptanceCommentEditSchema,
    AcceptanceCommentListQuerySchema,
    AcceptanceCommentListSchema,
    AcceptanceCommentSchema,
)

acceptance_comment_ns = Namespace(
    "acceptance_comments", path="/acceptances", description="Acceptance comment stream"
)
attachment_model = acceptance_comment_ns.model(
    "AcceptanceCommentAttachment",
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
comment_model = acceptance_comment_ns.model(
    "AcceptanceComment",
    {
        "acceptance_comment_id": fields.String(required=True),
        "text": fields.String(required=True),
        "created_by": fields.String(required=True),
        "author_name": fields.String,
        "created_at": fields.Integer(required=True),
        "updated_at": fields.Integer,
        "browser_id": fields.String,
        "attachments": fields.List(fields.Nested(attachment_model), required=True),
    },
)
comment_list_model = acceptance_comment_ns.model(
    "AcceptanceCommentList",
    {
        "total": fields.Integer(required=True),
        "comments": fields.List(fields.Nested(comment_model), required=True),
    },
)
comment_message_model = acceptance_comment_ns.model(
    "AcceptanceCommentMessage", {"msg": fields.String(required=True)}
)
comment_create_model = acceptance_comment_ns.model(
    "AcceptanceCommentCreate", {"text": fields.String(required=True)}
)


@acceptance_comment_ns.route("/<string:acceptance_id>/comments")
class AcceptanceCommentCollection(Resource):
    @api_key_or_jwt_required
    @acceptance_comment_ns.response(200, "OK", comment_list_model)
    def get(self, acceptance_id: str):
        try:
            offset, limit = load_pagination_query(AcceptanceCommentListQuerySchema())
            total, comments = ReportCommentService().list(
                "acceptance",
                parse_uuid(acceptance_id),
                comment_actor(),
                offset,
                limit,
            )
            return AcceptanceCommentListSchema().dump(
                {"total": total, "comments": comments}
            )
        except CommentError as error:
            return map_comment_error(error)
        except Exception as error:
            return map_comment_error(error)

    @api_key_or_jwt_required
    @acceptance_comment_ns.expect(comment_create_model, validate=True)
    @acceptance_comment_ns.response(201, "Created", comment_model)
    def post(self, acceptance_id: str):
        try:
            payload = load_payload(AcceptanceCommentCreateSchema())
            current_browser_id, needs_cookie = browser_id()
            comment = ReportCommentService().create(
                "acceptance",
                parse_uuid(acceptance_id),
                comment_actor(),
                str(payload["text"]),
                current_browser_id,
            )
            if needs_cookie:
                set_browser_id_cookie(current_browser_id)
            return AcceptanceCommentSchema().dump(comment), 201
        except CommentError as error:
            return map_comment_error(error)
        except Exception as error:
            return map_comment_error(error)


@acceptance_comment_ns.route("/comments/<string:comment_id>")
class AcceptanceCommentItem(Resource):
    @api_key_or_jwt_required
    @acceptance_comment_ns.expect(comment_create_model, validate=True)
    @acceptance_comment_ns.response(200, "OK", comment_model)
    def patch(self, comment_id: str):
        try:
            payload = load_payload(AcceptanceCommentEditSchema())
            comment = ReportCommentService().edit(
                "acceptance",
                parse_uuid(comment_id),
                comment_actor(),
                str(payload["text"]),
            )
            return AcceptanceCommentSchema().dump(comment)
        except CommentError as error:
            return map_comment_error(error)
        except Exception as error:
            return map_comment_error(error)

    @api_key_or_jwt_required
    @acceptance_comment_ns.marshal_with(comment_message_model)
    def delete(self, comment_id: str):
        try:
            ReportCommentService().delete(
                "acceptance", parse_uuid(comment_id), comment_actor()
            )
            return {"msg": "Comment deleted successfully"}, 200
        except CommentError as error:
            return map_comment_error(error)
        except Exception as error:
            return map_comment_error(error)


@acceptance_comment_ns.route("/comments/<string:comment_id>/attachments")
class AcceptanceCommentAttachmentCollection(Resource):
    @api_key_or_jwt_required
    @acceptance_comment_ns.expect(comment_attachment_parser)
    @acceptance_comment_ns.doc(consumes=["multipart/form-data"])
    @acceptance_comment_ns.response(201, "Created", comment_model)
    def post(self, comment_id: str):
        try:
            files = request.files.getlist("files")
            if not files:
                return {"msg": "At least one file is required"}, 400
            comment = ReportCommentService().upload(
                "acceptance",
                parse_uuid(comment_id),
                comment_actor(),
                [
                    UploadFile(file.filename or "", file.read(), file.mimetype)
                    for file in files
                ],
            )
            return AcceptanceCommentSchema().dump(comment), 201
        except CommentError as error:
            return map_comment_error(error)
        except Exception as error:
            return map_comment_error(error)


@acceptance_comment_ns.route(
    "/comments/<string:comment_id>/attachments/<string:attachment_id>/download"
)
class AcceptanceCommentAttachmentDownload(Resource):
    @api_key_or_jwt_required
    def get(self, comment_id: str, attachment_id: str):
        try:
            content, filename, content_type = ReportCommentService().download(
                "acceptance",
                parse_uuid(comment_id),
                parse_uuid(attachment_id),
                comment_actor(),
            )
            return send_file(
                BytesIO(content),
                mimetype=content_type,
                as_attachment=False,
                download_name=filename,
            )
        except CommentError as error:
            return map_comment_error(error)
        except Exception as error:
            return map_comment_error(error)
