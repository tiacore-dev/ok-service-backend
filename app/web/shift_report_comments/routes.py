from io import BytesIO

from flask import request, send_file
from flask_restx import Namespace, Resource, fields

from app.decorators import api_key_or_jwt_required
from app.use_cases.attachments import UploadFile
from app.use_cases.report_comments.service import CommentError, ReportCommentService
from app.web.utils.report_comments import (
    browser_id,
    comment_actor,
    load_pagination_query,
    load_payload,
    map_comment_error,
    parse_uuid,
    set_browser_id_cookie,
)

from .schemas import (
    ShiftReportCommentCreateSchema,
    ShiftReportCommentEditSchema,
    ShiftReportCommentListQuerySchema,
    ShiftReportCommentListSchema,
    ShiftReportCommentSchema,
)

shift_comment_ns = Namespace(
    "shift_report_comments",
    path="/shift_reports",
    description="Shift report comment stream",
)
attachment_model = shift_comment_ns.model(
    "ShiftReportCommentAttachment",
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
comment_model = shift_comment_ns.model(
    "ShiftReportComment",
    {
        "shift_report_comment_id": fields.String(required=True),
        "text": fields.String(required=True),
        "created_by": fields.String(required=True),
        "author_name": fields.String,
        "created_at": fields.Integer(required=True),
        "updated_at": fields.Integer,
        "browser_id": fields.String,
        "attachments": fields.List(fields.Nested(attachment_model), required=True),
    },
)
comment_list_model = shift_comment_ns.model(
    "ShiftReportCommentList",
    {
        "total": fields.Integer(required=True),
        "comments": fields.List(fields.Nested(comment_model), required=True),
    },
)
comment_message_model = shift_comment_ns.model(
    "ShiftReportCommentMessage", {"msg": fields.String(required=True)}
)
comment_create_model = shift_comment_ns.model(
    "ShiftReportCommentCreate", {"text": fields.String(required=True)}
)


@shift_comment_ns.route("/<string:shift_report_id>/comments")
class ShiftReportCommentCollection(Resource):
    @api_key_or_jwt_required
    @shift_comment_ns.response(200, "OK", comment_list_model)
    def get(self, shift_report_id: str):
        try:
            offset, limit = load_pagination_query(ShiftReportCommentListQuerySchema())
            total, comments = ReportCommentService().list(
                "shift",
                parse_uuid(shift_report_id),
                comment_actor(),
                offset,
                limit,
            )
            return ShiftReportCommentListSchema().dump(
                {"total": total, "comments": comments}
            )
        except CommentError as error:
            return map_comment_error(error)
        except Exception as error:
            return map_comment_error(error)

    @api_key_or_jwt_required
    @shift_comment_ns.expect(comment_create_model, validate=True)
    @shift_comment_ns.response(201, "Created", comment_model)
    def post(self, shift_report_id: str):
        try:
            payload = load_payload(ShiftReportCommentCreateSchema())
            current_browser_id, needs_cookie = browser_id()
            comment = ReportCommentService().create(
                "shift",
                parse_uuid(shift_report_id),
                comment_actor(),
                str(payload["text"]),
                current_browser_id,
            )
            if needs_cookie:
                set_browser_id_cookie(current_browser_id)
            return ShiftReportCommentSchema().dump(comment), 201
        except CommentError as error:
            return map_comment_error(error)
        except Exception as error:
            return map_comment_error(error)


@shift_comment_ns.route("/comments/<string:comment_id>")
class ShiftReportCommentItem(Resource):
    @api_key_or_jwt_required
    @shift_comment_ns.expect(comment_create_model, validate=True)
    @shift_comment_ns.response(200, "OK", comment_model)
    def patch(self, comment_id: str):
        try:
            payload = load_payload(ShiftReportCommentEditSchema())
            comment = ReportCommentService().edit(
                "shift", parse_uuid(comment_id), comment_actor(), str(payload["text"])
            )
            return ShiftReportCommentSchema().dump(comment)
        except CommentError as error:
            return map_comment_error(error)
        except Exception as error:
            return map_comment_error(error)

    @api_key_or_jwt_required
    @shift_comment_ns.marshal_with(comment_message_model)
    def delete(self, comment_id: str):
        try:
            ReportCommentService().delete(
                "shift", parse_uuid(comment_id), comment_actor()
            )
            return {"msg": "Comment deleted successfully"}, 200
        except CommentError as error:
            return map_comment_error(error)
        except Exception as error:
            return map_comment_error(error)


@shift_comment_ns.route("/comments/<string:comment_id>/attachments")
class ShiftReportCommentAttachmentCollection(Resource):
    @api_key_or_jwt_required
    @shift_comment_ns.response(201, "Created", comment_model)
    def post(self, comment_id: str):
        try:
            files = request.files.getlist("files")
            if not files:
                return {"msg": "At least one file is required"}, 400
            comment = ReportCommentService().upload(
                "shift",
                parse_uuid(comment_id),
                comment_actor(),
                [
                    UploadFile(file.filename or "", file.read(), file.mimetype)
                    for file in files
                ],
            )
            return ShiftReportCommentSchema().dump(comment), 201
        except CommentError as error:
            return map_comment_error(error)
        except Exception as error:
            return map_comment_error(error)


@shift_comment_ns.route(
    "/comments/<string:comment_id>/attachments/<string:attachment_id>/download"
)
class ShiftReportCommentAttachmentDownload(Resource):
    @api_key_or_jwt_required
    def get(self, comment_id: str, attachment_id: str):
        try:
            content, filename, content_type = ReportCommentService().download(
                "shift",
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
