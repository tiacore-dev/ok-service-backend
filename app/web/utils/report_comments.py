from __future__ import annotations

import json
from typing import cast
from uuid import UUID, uuid4

from flask import after_this_request, current_app, g, request
from flask_jwt_extended import get_jwt_identity
from flask_restx import reqparse
from marshmallow import Schema, ValidationError
from werkzeug.datastructures import FileStorage

from app.domain.attachments import AttachmentStorageError
from app.s3.s3_manager import FileValidationError
from app.use_cases.report_comments.service import CommentActor, CommentError

comment_attachment_parser = reqparse.RequestParser()
comment_attachment_parser.add_argument(
    "files",
    type=FileStorage,
    location="files",
    required=True,
    help="One or more files; repeat the files field for multiple attachments",
)


def current_identity() -> dict[str, object]:
    value = (
        getattr(g, "api_key_identity_json", None)
        if getattr(g, "auth_via_api_key", False)
        else get_jwt_identity()
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


def comment_actor() -> CommentActor:
    identity = current_identity()
    try:
        user_id = UUID(str(identity["user_id"]))
    except (KeyError, ValueError) as error:
        raise CommentError("Current user id is required", 403) from error
    return CommentActor(user_id=user_id, role=str(identity.get("role", "")))


def parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except (TypeError, ValueError) as error:
        raise CommentError("Invalid UUID format", 400) from error


def browser_id() -> tuple[UUID, bool]:
    raw_value = request.cookies.get(current_app.config["BROWSER_ID_COOKIE_NAME"])
    try:
        return UUID(raw_value), False
    except (TypeError, ValueError):
        return uuid4(), True


def set_browser_id_cookie(value: UUID) -> None:
    @after_this_request
    def set_cookie(response):
        response.set_cookie(
            current_app.config["BROWSER_ID_COOKIE_NAME"],
            str(value),
            max_age=current_app.config["BROWSER_ID_COOKIE_MAX_AGE"],
            secure=True,
            httponly=True,
            samesite="Lax",
        )
        return response


def load_payload(schema: Schema) -> dict[str, object]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise CommentError("Request body is required", 400)
    try:
        loaded = schema.load(payload)
    except ValidationError as error:
        raise CommentError(str(error.messages), 400) from error
    if not isinstance(loaded, dict):
        raise CommentError("Request body must be an object", 400)
    return cast(dict[str, object], loaded)


def load_pagination_query(schema: Schema) -> tuple[int, int]:
    try:
        loaded = schema.load(request.args.to_dict())
    except ValidationError as error:
        raise CommentError(str(error.messages), 400) from error
    if not isinstance(loaded, dict):
        raise CommentError("Query parameters are invalid", 400)
    offset = loaded.get("offset")
    limit = loaded.get("limit")
    if not isinstance(offset, int) or not isinstance(limit, int):
        raise CommentError("offset and limit must be integers", 400)
    return offset, limit


def map_comment_error(error: Exception):
    if isinstance(error, CommentError):
        return {"msg": str(error)}, error.status
    if isinstance(error, AttachmentStorageError):
        return {"msg": str(error)}, 503
    if isinstance(error, (FileValidationError, ValidationError, ValueError)):
        return {"msg": str(error)}, 400
    return {"msg": "Internal server error"}, 500
