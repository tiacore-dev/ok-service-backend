import json
import logging
from dataclasses import asdict
from io import BytesIO
from typing import NotRequired, TypedDict, cast
from uuid import UUID

from flask import request, send_file
from flask_restx import Model, Resource, fields, inputs, reqparse
from marshmallow import ValidationError
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.adapters.templates.parameters import MarshmallowTemplateParametersProvider
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
from app.use_cases.templates.parameters import GetTemplateParametersUseCase
from app.utils.helpers import generate_swagger_model
from app.web._typing import to_plain_dict

from .auth import template_auth_required
from .namespace import template_ns as template_files_ns
from .schemas import (
    TemplateCreateSchema,
    TemplateEditSchema,
    TemplateFilterSchema,
    TemplateParamsQuerySchema,
)

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
template_params_model = Model(
    "StoredTemplateParams",
    {
        "template_type": fields.String(
            required=True, enum=[value.value for value in TemplateTypes]
        ),
        "parameters": fields.List(
            fields.String(),
            required=True,
            description="Пути полей; элементы массивов обозначаются [i]",
        ),
        "schema": fields.Raw(
            required=True,
            description="Схема данных с русскими title, example и alias-свойствами массивов",
        ),
    },
)
for model in (
    create_model,
    edit_model,
    template_model,
    template_type_model,
    template_types_model,
    template_params_model,
):
    template_files_ns.models[model.name] = model


def _upload_parser(required: bool):
    parser = reqparse.RequestParser()
    parser.add_argument("file", type=FileStorage, location="files", required=required)
    if required:
        parser.add_argument(
            "name", location="form", required=True, help="Название шаблона"
        )
        parser.add_argument(
            "template_type",
            location="form",
            required=True,
            choices=[value.value for value in TemplateTypes],
            help="Тип шаблона",
        )
        parser.add_argument("description", location="form", help="Описание")
        parser.add_argument("output_file_name", location="form", help="Имя результата")
        for name, label in (
            ("is_horizontal", "Альбомная ориентация"),
            ("is_pdf", "Формировать PDF"),
            ("is_default", "Шаблон по умолчанию"),
        ):
            parser.add_argument(
                name, type=inputs.boolean, location="form", default=False, help=label
            )
        return parser
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
params_parser = reqparse.RequestParser()
params_parser.add_argument(
    "template_type",
    required=True,
    choices=[value.value for value in TemplateTypes],
    location="args",
)


class TemplateFilterPayload(TypedDict):
    offset: int
    limit: int
    template_type: NotRequired[TemplateTypes]


class TemplateParamsPayload(TypedDict):
    template_type: TemplateTypes


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
        allowed_fields = (
            set(TemplateCreateSchema().fields) | {"data"} if create else {"data"}
        )
        if set(request.form) - allowed_fields or set(request.files) - {"file"}:
            raise ValueError("Unknown form fields")
        if (
            any(len(request.form.getlist(key)) > 1 for key in request.form)
            or len(request.files.getlist("file")) > 1
        ):
            raise ValueError("Form fields and file must not be repeated")
        if "data" in request.form:
            if len(request.form) > 1:
                raise ValueError("Do not mix data with separate metadata fields")
            try:
                raw = json.loads(request.form["data"])
            except ValueError as error:
                raise ValueError("data must contain a JSON object") from error
        else:
            raw = {
                key: value
                for key, value in request.form.to_dict().items()
                if key not in {"description", "output_file_name"} or value.strip()
            }
        uploaded = request.files.get("file")
    elif not create and request.is_json:
        raw = request.get_json(silent=True)
        uploaded = None
    else:
        raise ValueError("Use multipart/form-data with metadata fields and file")
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
    @template_auth_required
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
    @template_auth_required
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
    @template_auth_required
    @admin_or_manager_required
    @template_files_ns.marshal_with(template_types_model)
    def get(self):
        return {
            "template_types": [
                {"value": item.value, "label": item.label()} for item in TemplateTypes
            ]
        }, 200


@template_files_ns.route("/params")
class TemplateParams(Resource):
    @template_auth_required
    @admin_or_manager_required
    @template_files_ns.expect(params_parser)
    @template_files_ns.response(200, "Параметры печатных данных", template_params_model)
    @template_files_ns.response(400, "Некорректный или отсутствующий тип шаблона")
    def get(self):
        try:
            if len(request.args.getlist("template_type")) != 1:
                raise ValueError("Exactly one template_type is required")
            query = cast(
                TemplateParamsPayload,
                TemplateParamsQuerySchema().load(request.args.to_dict()),
            )
            result = GetTemplateParametersUseCase(
                MarshmallowTemplateParametersProvider()
            ).execute(query["template_type"])
            return {
                "template_type": result.template_type.value,
                "parameters": result.parameters,
                "schema": result.schema,
            }, 200
        except REQUEST_ERRORS as error:
            return _error(error)


@template_files_ns.route("/<string:template_id>/view")
class TemplateView(Resource):
    @template_auth_required
    @admin_or_manager_required
    @template_files_ns.response(200, "Метаданные шаблона", template_model)
    def get(self, template_id):
        try:
            return _response(_use_case().get(UUID(template_id))), 200
        except REQUEST_ERRORS as error:
            return _error(error)


@template_files_ns.route("/<string:template_id>/edit")
class TemplateEdit(Resource):
    @template_auth_required
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
    @template_auth_required
    @admin_or_manager_required
    def delete(self, template_id):
        try:
            _use_case().delete(UUID(template_id))
            return {"msg": "Template deleted successfully"}, 200
        except REQUEST_ERRORS as error:
            return _error(error)


@template_files_ns.route("/<string:template_id>/download")
class TemplateDownload(Resource):
    @template_auth_required
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
