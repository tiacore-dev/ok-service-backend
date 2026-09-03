from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import Any
from uuid import UUID

from flask import g, request, send_file
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Model, Namespace, Resource, fields, reqparse
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.adapters.attachments import S3AttachmentStorage, SQLAlchemyAttachmentRepository
from app.decorators import api_key_or_jwt_required
from app.domain.attachments import (
    Attachment,
    AttachmentConflictError,
    AttachmentForbiddenError,
    AttachmentNotFoundError,
    AttachmentStorageError,
)
from app.s3.s3_manager import FileValidationError
from app.use_cases.attachments import AttachmentActor, AttachmentUseCase, UploadFile

from .contract import attachment_view_model

logger = logging.getLogger("ok_service")

project_attachment_ns = Namespace(
    "project_attachments", path="/projects", description="Project attachments"
)
shift_report_attachment_ns = Namespace(
    "shift_report_attachments",
    path="/shift_reports",
    description="Shift report attachments",
)
object_attachment_ns = Namespace(
    "object_attachments", path="/objects", description="Object attachments"
)
place_attachment_ns = Namespace(
    "place_attachments", path="/places", description="Place attachments"
)
acceptance_attachment_ns = Namespace(
    "work_acceptance_attachments",
    path="/acceptances",
    description="Work acceptance attachments",
)

attachment_model = Model(
    "Attachment",
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
attachment_list_model = Model(
    "AttachmentList",
    {
        "msg": fields.String(required=True),
        "attachments": fields.List(fields.Nested(attachment_model)),
    },
)
attachment_url_model = Model(
    "AttachmentDownloadUrl",
    {"msg": fields.String(required=True), "url": fields.String(required=True)},
)
attachment_message_model = Model(
    "AttachmentMessage", {"msg": fields.String(required=True)}
)

for namespace in (
    project_attachment_ns,
    shift_report_attachment_ns,
    object_attachment_ns,
    place_attachment_ns,
    acceptance_attachment_ns,
):
    for model in (
        attachment_model,
        attachment_list_model,
        attachment_url_model,
        attachment_message_model,
        attachment_view_model,
    ):
        namespace.models[model.name] = model

upload_parser = reqparse.RequestParser()
upload_parser.add_argument(
    "files",
    type=FileStorage,
    location="files",
    required=True,
    help="One or more attachment files",
)


def _identity() -> dict[str, Any]:
    value = (
        getattr(g, "api_key_identity_json", None)
        if getattr(g, "auth_via_api_key", False)
        else _get_jwt_identity()
    )
    if isinstance(value, dict):
        return value
    if isinstance(value, (str, bytes, bytearray)):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _actor() -> AttachmentActor:
    identity = _identity()
    user_id = identity.get("user_id")
    if not user_id:
        raise AttachmentForbiddenError("Current user id is required")
    return AttachmentActor(
        user_id=UUID(str(user_id)), role=str(identity.get("role", ""))
    )


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as error:
        raise ValueError("Invalid UUID format") from error


def _use_case() -> AttachmentUseCase:
    return AttachmentUseCase(SQLAlchemyAttachmentRepository(), S3AttachmentStorage())


def _response(attachment: Attachment) -> dict[str, object]:
    return {
        "attachment_id": str(attachment.attachment_id),
        "name": attachment.name,
        "file_size": attachment.file_size,
        "checksum": attachment.checksum,
        "meta": attachment.meta,
        "created_at": attachment.created_at,
        "created_by": str(attachment.created_by),
    }


def _error(error: Exception):
    if isinstance(error, RequestEntityTooLarge):
        return {"msg": str(error)}, 413
    if isinstance(error, AttachmentNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, AttachmentForbiddenError):
        return {"msg": str(error)}, 403
    if isinstance(error, AttachmentConflictError):
        return {"msg": str(error)}, 409
    if isinstance(error, AttachmentStorageError):
        return {"msg": str(error)}, 503
    if isinstance(error, (BadRequest, FileValidationError, ValueError)):
        return {"msg": str(error)}, 400
    return {"msg": "Internal server error"}, 500


def _upload(target_type: str, target_id: str):
    request_context = {
        "target_type": target_type,
        "target_id": target_id,
        "method": request.method,
        "path": request.path,
    }
    logger.debug("Attachment upload started: %s", request_context)
    try:
        files = request.files.getlist("files")
        logger.debug(
            "Attachment upload files parsed: count=%d files=%s",
            len(files),
            [
                {
                    "name": file.filename,
                    "content_type": file.mimetype,
                    "content_length": file.content_length,
                }
                for file in files
            ],
        )
        actor = _actor()
        logger.debug(
            "Attachment upload actor resolved: user_id=%s role=%s",
            actor.user_id,
            actor.role,
        )
        uploaded = _use_case().upload(
            target_type,
            _uuid(target_id),
            [
                UploadFile(
                    name=file.filename or "",
                    content=file.read(),
                    content_type=file.mimetype,
                )
                for file in files
            ],
            actor,
        )
        logger.info(
            "Attachment upload completed: target_type=%s target_id=%s count=%d",
            target_type,
            target_id,
            len(uploaded),
        )
        return {
            "msg": "Attachments uploaded successfully",
            "attachments": [_response(attachment) for attachment in uploaded],
        }, 200
    except Exception as error:
        if isinstance(
            error,
            (
                AttachmentNotFoundError,
                AttachmentForbiddenError,
                AttachmentConflictError,
                AttachmentStorageError,
                BadRequest,
                RequestEntityTooLarge,
                FileValidationError,
                ValueError,
            ),
        ):
            logger.warning(
                "Attachment upload rejected: %s error=%s",
                request_context,
                error,
            )
        else:
            logger.exception(
                "Attachment upload failed unexpectedly: %s", request_context
            )
        return _error(error)


def _list(target_type: str, target_id: str):
    try:
        attachments = _use_case().list(target_type, _uuid(target_id), _actor())
        return {
            "msg": "Attachments found successfully",
            "attachments": [_response(attachment) for attachment in attachments],
        }, 200
    except Exception as error:
        return _error(error)


def _download(target_type: str, target_id: str, attachment_id: str):
    request_context = {
        "target_type": target_type,
        "target_id": target_id,
        "attachment_id": attachment_id,
        "method": request.method,
        "path": request.path,
    }
    logger.debug("Attachment download started: %s", request_context)
    try:
        content, filename, content_type = _use_case().download_bytes(
            target_type, _uuid(target_id), _uuid(attachment_id), _actor()
        )
        response = send_file(
            BytesIO(content),
            mimetype=content_type,
            as_attachment=False,
            download_name=filename,
        )
        logger.info(
            "Attachment download completed: target_type=%s target_id=%s "
            "attachment_id=%s bytes=%d",
            target_type,
            target_id,
            attachment_id,
            len(content),
        )
        return response
    except Exception as error:
        if isinstance(
            error,
            (
                AttachmentNotFoundError,
                AttachmentForbiddenError,
                AttachmentConflictError,
                AttachmentStorageError,
                BadRequest,
                ValueError,
            ),
        ):
            logger.warning(
                "Attachment download rejected: %s error=%s",
                request_context,
                error,
            )
        else:
            logger.exception(
                "Attachment download failed unexpectedly: %s", request_context
            )
        return _error(error)


def _delete(target_type: str, target_id: str, attachment_id: str):
    try:
        _use_case().delete(
            target_type, _uuid(target_id), _uuid(attachment_id), _actor()
        )
        return {"msg": "Attachment deleted successfully"}, 200
    except Exception as error:
        return _error(error)


def _register_routes(namespace: Namespace, target_type: str, id_name: str) -> None:
    collection_path = f"/<string:{id_name}>/attachments"
    item_path = f"/<string:{id_name}>/attachments/<string:attachment_id>"

    @namespace.route(collection_path)
    class AttachmentCollection(Resource):
        @api_key_or_jwt_required
        @namespace.expect(upload_parser)
        @namespace.doc(consumes=["multipart/form-data"])
        @namespace.marshal_with(attachment_list_model)
        def post(self, **kwargs):
            return _upload(target_type, kwargs[id_name])

        @api_key_or_jwt_required
        @namespace.marshal_with(attachment_list_model)
        def get(self, **kwargs):
            return _list(target_type, kwargs[id_name])

    @namespace.route(f"{item_path}/download")
    class AttachmentDownload(Resource):
        @api_key_or_jwt_required
        def get(self, **kwargs):
            return _download(target_type, kwargs[id_name], kwargs["attachment_id"])

    @namespace.route(item_path)
    class AttachmentDelete(Resource):
        @api_key_or_jwt_required
        @namespace.marshal_with(attachment_message_model)
        def delete(self, **kwargs):
            return _delete(target_type, kwargs[id_name], kwargs["attachment_id"])


_register_routes(project_attachment_ns, "project", "project_id")
_register_routes(shift_report_attachment_ns, "shift_report", "shift_report_id")
_register_routes(object_attachment_ns, "object", "object_id")
_register_routes(place_attachment_ns, "place", "place_id")
_register_routes(acceptance_attachment_ns, "acceptance", "acceptance_id")
