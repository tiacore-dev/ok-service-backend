from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import Any, NotRequired, TypedDict, cast

from flask import current_app, request, send_file
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError

from app.adapters.template_generation import HTTPTemplateGenerator
from app.domain.template_generation import TemplateGenerationError
from app.schemas.template_schemas import TemplateGenerateSchema
from app.use_cases.template_generation import (
    GenerateTemplateUseCase,
    TemplateGenerateCommand,
)
from app.utils.helpers import generate_swagger_model
from app.web._typing import get_optional_bool, get_optional_str, to_plain_dict

logger = logging.getLogger("ok_service")

template_ns = Namespace("templates", description="template management operations")
template_generate_model = generate_swagger_model(
    TemplateGenerateSchema(), "templateCreate"
)
template_ns.models[template_generate_model.name] = template_generate_model


class TemplateGeneratePayload(TypedDict):
    name: str
    document_data: dict[str, Any]
    is_pdf: bool
    url: NotRequired[str | None]
    file_name: NotRequired[str | None]


def _get_current_user() -> dict[str, Any]:
    identity = _get_jwt_identity()
    if isinstance(identity, dict):
        return identity
    if isinstance(identity, (str, bytes, bytearray)):
        try:
            parsed = json.loads(identity)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _generator() -> HTTPTemplateGenerator:
    return HTTPTemplateGenerator(current_app.config.get("TEMPLATE_SERVICE_URL"))


def _command_from_payload(payload: TemplateGeneratePayload) -> TemplateGenerateCommand:
    return TemplateGenerateCommand(
        url=get_optional_str(payload, "url"),
        file_name=get_optional_str(payload, "file_name"),
        name=payload["name"],
        is_pdf=bool(get_optional_bool(payload, "is_pdf")),
        document_data=payload["document_data"],
    )


@template_ns.route("/generate")
class TemplateGenerate(Resource):
    @jwt_required()
    @template_ns.expect(template_generate_model)
    @template_ns.response(400, "Bad request, invalid data.")
    @template_ns.response(500, "Internal Server Error")
    @template_ns.doc(description="Генерация файла по шаблону")
    @template_ns.response(
        201,
        "Файл успешно сгенерирован",
        headers={
            "Content-Disposition": 'attachment; filename="output.docx"',
            "Content-Type": """application/vnd.openxmlformats-officedocument.
            wordprocessingml.document""",
        },
    )
    def post(self):
        current_user = _get_current_user()
        schema = TemplateGenerateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(TemplateGeneratePayload, schema.load(raw_payload))
            document_bytes = GenerateTemplateUseCase(generator=_generator()).execute(
                _command_from_payload(data)
            )
        except ValidationError as err:
            logger.error(
                f"Ошибка валидации при генерации шаблона: {err.messages}",
                extra={"login": current_user.get("login")},
            )
            return {"msg": "Некорректные данные", "errors": err.messages}, 400
        except ValueError as err:
            logger.error(
                f"Ошибка при разборе запроса на генерацию шаблона: {err}",
                extra={"login": current_user.get("login")},
            )
            return {"msg": str(err)}, 400
        except TemplateGenerationError as err:
            logger.error(
                f"Ошибка при генерации шаблона: {err}",
                extra={"login": current_user.get("login")},
            )
            return {"msg": "Ошибка при генерации файла"}, 500

        return send_file(
            BytesIO(document_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name="output.docx",
        )
