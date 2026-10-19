import json
import logging
from dataclasses import asdict
from functools import wraps
from io import BytesIO
from typing import NotRequired, TypedDict, cast
from uuid import UUID

from flask import request, send_file
from flask_jwt_extended import verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from flask_restx import Model, Namespace, Resource, fields, reqparse
from jwt.exceptions import PyJWTError
from marshmallow import ValidationError
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.adapters.templates.s3_storage import S3TemplateStorage
from app.adapters.templates.sqlalchemy_repository import SQLAlchemyTemplateRepository
from app.decorators import admin_or_manager_required
from app.domain.templates import (
    Template,
    TemplateConflictError,
    TemplateNotFoundError,
    TemplateStorageError,
    TemplateTypes,
)
from app.s3.s3_manager import MAX_FILE_SIZE_BYTES
from app.use_cases.templates.dto import TemplateChanges
from app.use_cases.templates.manage_templates import TemplateUseCase
from app.utils.helpers import generate_swagger_model
from app.web._typing import to_plain_dict

from .schemas import TemplateCreateSchema, TemplateEditSchema, TemplateFilterSchema

logger = logging.getLogger("ok_service")
REQUEST_ERRORS = (
    TemplateNotFoundError,
    TemplateConflictError,
    TemplateStorageError,
    ValidationError,
    ValueError,
    BadRequest,
    RequestEntityTooLarge,
)
template_files_ns = Namespace(
    "template_files",
    path="/templates",
    description="Хранение шаблонов: admin и manager",
)

create_model = generate_swagger_model(TemplateCreateSchema(), "StoredTemplateCreate")
edit_model = generate_swagger_model(TemplateEditSchema(), "StoredTemplateEdit")
# The shared generator does not preserve required flags or enum constraints.
create_model["name"] = fields.String(required=True, min_length=1, max_length=255)
create_model["template_type"] = fields.String(
    required=True, enum=[v.value for v in TemplateTypes]
)
edit_model["name"] = fields.String(min_length=1, max_length=255)
template_model = Model(
    "StoredTemplate",
    {
        "id": fields.String(),
        "name": fields.String(),
        "description": fields.String(),
        "template_type": fields.String(enum=[v.value for v in TemplateTypes]),
        "template_type_label": fields.String(),
        "s3_key": fields.String(),
        "file_name": fields.String(),
        "content_type": fields.String(),
        "output_file_name": fields.String(),
        "is_horizontal": fields.Boolean(),
        "is_pdf": fields.Boolean(),
        "is_default": fields.Boolean(),
    },
)
template_type_model = Model(
    "StoredTemplateType",
    {
        "value": fields.String(required=True, enum=[v.value for v in TemplateTypes]),
        "label": fields.String(required=True),
    },
)
template_types_model = Model(
    "StoredTemplateTypes",
    {
        "template_types": fields.List(
            fields.Nested(template_type_model), required=True
        ),
    },
)
for model in (
    create_model,
    edit_model,
    template_model,
    template_type_model,
    template_types_model,
):
    template_files_ns.models[model.name] = model


def _upload_parser(required: bool):
    parser = reqparse.RequestParser()
    parser.add_argument("file", type=FileStorage, location="files", required=required)
    parser.add_argument(
        "data",
        type=str,
        location="form",
        required=required,
        help=(
            'JSON: {"name":"Шаблон","template_type":"work_types",'
            '"description":null,"output_file_name":null,"is_horizontal":false,'
            '"is_pdf":false,"is_default":false}. '
            "Create requires name and template_type; PATCH forbids template_type and accepts partial metadata."
        ),
    )
    return parser


create_parser = _upload_parser(True)
edit_parser = _upload_parser(False)
filter_parser = reqparse.RequestParser()
filter_parser.add_argument("template_type", choices=[v.value for v in TemplateTypes])
filter_parser.add_argument("offset", type=int, default=0)
filter_parser.add_argument("limit", type=int, default=100)


class TemplateFilterPayload(TypedDict):
    offset: int
    limit: int
    template_type: NotRequired[TemplateTypes]


def _jwt_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except (JWTExtendedException, PyJWTError):
            return {"msg": "Unauthorized"}, 401
        return func(*args, **kwargs)

    return wrapper


def _use_case() -> TemplateUseCase:
    return TemplateUseCase(SQLAlchemyTemplateRepository(), S3TemplateStorage())


def _response(template: Template) -> dict:
    data = asdict(template)
    data["id"] = str(template.id)
    data["template_type"] = template.template_type.value
    data["template_type_label"] = template.template_type.label()
    return data


def _payload(create: bool) -> tuple[dict, tuple[bytes, str, str | None] | None]:
    if request.mimetype == "multipart/form-data":
        if set(request.form) - {"data"} or set(request.files) - {"file"}:
            raise ValueError("Only data and file fields are allowed")
        if (
            len(request.form.getlist("data")) > 1
            or len(request.files.getlist("file")) > 1
        ):
            raise ValueError("Only one data field and one file are allowed")
        try:
            raw = json.loads(request.form.get("data", "{}"))
        except ValueError as error:
            raise ValueError("data must contain a JSON object") from error
        uploaded = request.files.get("file")
    elif not create and request.is_json:
        raw = request.get_json(silent=True)
        uploaded = None
    else:
        raise ValueError("Use multipart/form-data with data (JSON) and file")
    schema = TemplateCreateSchema() if create else TemplateEditSchema()
    data = schema.load(to_plain_dict(raw, "Metadata must be a JSON object"))
    file = None
    if uploaded is not None:
        content = uploaded.stream.read(MAX_FILE_SIZE_BYTES + 1)
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise RequestEntityTooLarge()
        file = (content, uploaded.filename or "", uploaded.mimetype)
    if create and file is None:
        raise ValueError("file is required")
    return cast(dict, data), file


def _error(error: Exception):
    if isinstance(error, TemplateNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, TemplateConflictError):
        return {"msg": str(error)}, 409
    if isinstance(error, TemplateStorageError):
        logger.exception("Template storage request failed")
        return {"msg": "Template storage unavailable"}, 503
    if isinstance(error, RequestEntityTooLarge):
        return {"msg": "File exceeds 100 MiB"}, 413
    if isinstance(error, ValidationError):
        return {"errors": error.messages}, 400
    if isinstance(error, (ValueError, BadRequest)):
        return {"msg": str(error)}, 400
    logger.exception("Template request failed")
    return {"msg": "Internal server error"}, 500


@template_files_ns.route("/add")
class TemplateAdd(Resource):
    @_jwt_required
    @admin_or_manager_required
    @template_files_ns.expect(create_parser)
    @template_files_ns.response(201, "Шаблон создан", template_model)
    def post(self):
        try:
            data, file = _payload(True)
            assert file is not None
            template_type = data.pop("template_type")
            name = data.pop("name")
            result = _use_case().create(
                template_type, name, cast(TemplateChanges, data), *file
            )
            return _response(result), 201
        except REQUEST_ERRORS as error:
            return _error(error)


@template_files_ns.route("/all")
class TemplateAll(Resource):
    @_jwt_required
    @admin_or_manager_required
    @template_files_ns.expect(filter_parser)
    def get(self):
        try:
            data = cast(
                TemplateFilterPayload,
                TemplateFilterSchema().load(request.args.to_dict()),
            )
            return {
                "templates": [
                    _response(item)
                    for item in _use_case().list(
                        data.get("template_type"), data["offset"], data["limit"]
                    )
                ]
            }, 200
        except REQUEST_ERRORS as error:
            return _error(error)


@template_files_ns.route("/types/all")
class TemplateTypesAll(Resource):
    @_jwt_required
    @admin_or_manager_required
    @template_files_ns.marshal_with(template_types_model)
    def get(self):
        return {
            "template_types": [
                {"value": item.value, "label": item.label()} for item in TemplateTypes
            ]
        }, 200


@template_files_ns.route("/<string:template_id>/view")
class TemplateView(Resource):
    @_jwt_required
    @admin_or_manager_required
    @template_files_ns.response(200, "Метаданные шаблона", template_model)
    def get(self, template_id):
        try:
            return _response(_use_case().get(UUID(template_id))), 200
        except REQUEST_ERRORS as error:
            return _error(error)


@template_files_ns.route("/<string:template_id>/edit")
class TemplateEdit(Resource):
    @_jwt_required
    @admin_or_manager_required
    @template_files_ns.expect(edit_parser)
    @template_files_ns.doc(
        consumes=["multipart/form-data", "application/json"],
        description="JSON StoredTemplateEdit либо multipart: data (JSON) и необязательный file. template_type неизменяем.",
    )
    @template_files_ns.response(200, "Шаблон обновлён", template_model)
    def patch(self, template_id):
        try:
            data, file = _payload(False)
            return _response(
                _use_case().update(UUID(template_id), cast(TemplateChanges, data), file)
            ), 200
        except REQUEST_ERRORS as error:
            return _error(error)


@template_files_ns.route("/<string:template_id>/delete/hard")
class TemplateDelete(Resource):
    @_jwt_required
    @admin_or_manager_required
    def delete(self, template_id):
        try:
            _use_case().delete(UUID(template_id))
            return {"msg": "Template deleted successfully"}, 200
        except REQUEST_ERRORS as error:
            return _error(error)


@template_files_ns.route("/<string:template_id>/download")
class TemplateDownload(Resource):
    @_jwt_required
    @admin_or_manager_required
    def get(self, template_id):
        try:
            content, filename, mime = _use_case().download(UUID(template_id))
            return send_file(
                BytesIO(content),
                mimetype=mime,
                as_attachment=True,
                download_name=filename,
            )
        except REQUEST_ERRORS as error:
            return _error(error)
