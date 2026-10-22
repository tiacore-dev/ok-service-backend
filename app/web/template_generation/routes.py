import logging
from typing import Any, NotRequired, TypedDict, cast
from uuid import UUID

from flask import Response, current_app, request
from flask_restx import Model, Resource, fields
from marshmallow import ValidationError

from app.adapters.template_generation import HTTPTemplateGenerator
from app.adapters.template_generation.data_repository import (
    MarshmallowDocumentDataSerializer,
    SQLAlchemyDocumentDataRepository,
)
from app.adapters.templates.s3_storage import S3TemplateStorage
from app.adapters.templates.sqlalchemy_repository import SQLAlchemyTemplateRepository
from app.decorators import admin_or_manager_required
from app.domain.template_generation import TemplateGenerationError
from app.domain.templates import (
    TemplateNotFoundError,
    TemplateStorageError,
    TemplateTypes,
)
from app.schemas.template_schemas import TemplateGenerateSchema
from app.use_cases.template_generation import GenerateTemplateUseCase
from app.use_cases.template_generation.build_data import BuildDocumentData
from app.use_cases.template_generation.dto import (
    GenerateDocumentCommand,
    GenerationParameters,
)
from app.web._typing import to_plain_dict
from app.web.templates.auth import template_auth_required
from app.web.templates.namespace import template_ns

logger = logging.getLogger("ok_service")


class TemplateGenerationPayload(TypedDict):
    template_type: TemplateTypes
    template_id: NotRequired[UUID]
    is_pdf: bool | None
    parameters: dict[str, Any]


parameters_model = Model(
    "TemplateGenerationParameters",
    {
        "shift_report_id": fields.String(
            description="Обязателен для shift_report", format="uuid"
        ),
        "date_from": fields.String(
            description="Начало периода включительно; обязательно для payroll, object_report, shift_report_list",
            format="date",
        ),
        "date_to": fields.String(
            description="Конец периода включительно; обязательно для payroll, object_report, shift_report_list",
            format="date",
        ),
        "user": fields.String(description="Обязателен для payroll", format="uuid"),
        "users": fields.List(
            fields.String,
            description="Фильтр исполнителей для object_report и shift_report_list",
        ),
        "projects": fields.List(
            fields.String,
            description="Фильтр спецификаций для object_report и shift_report_list",
        ),
    },
)
template_generate_model = Model(
    "TemplateGenerationRequest",
    {
        "template_type": fields.String(
            required=True, enum=[kind.value for kind in TemplateTypes]
        ),
        "template_id": fields.String(
            description="Если не передан — шаблон по умолчанию", format="uuid"
        ),
        "is_pdf": fields.Boolean(description="null или отсутствие — настройка шаблона"),
        "parameters": fields.Nested(parameters_model),
    },
)
for model in (parameters_model, template_generate_model):
    template_ns.models[model.name] = model


def _generator():
    return HTTPTemplateGenerator(
        current_app.config.get("TEMPLATE_SERVICE_NEW_URL"),
        current_app.config.get("TEMPLATE_SERVICE_API_KEY"),
    )


def _use_case():
    return GenerateTemplateUseCase(
        generator=_generator(),
        templates=SQLAlchemyTemplateRepository(),
        storage=S3TemplateStorage(),
        data_builder=BuildDocumentData(
            SQLAlchemyDocumentDataRepository(), MarshmallowDocumentDataSerializer()
        ),
    )


@template_ns.route("/generate-new")
class TemplateGenerateNew(Resource):
    @template_auth_required
    @admin_or_manager_required
    @template_ns.expect(template_generate_model)
    @template_ns.response(200, "Поток сгенерированного DOCX/XLSX/PDF")
    @template_ns.response(
        400, "Некорректные параметры, нет дефолтного шаблона или тип не совпадает"
    )
    @template_ns.response(403, "Недостаточно прав")
    @template_ns.response(404, "Шаблон не найден")
    @template_ns.response(500, "Ошибка генерации")
    def post(self):
        try:
            raw = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            loaded = TemplateGenerateSchema().load(raw)
            if not isinstance(loaded, dict):
                raise ValidationError("Тело запроса должно быть объектом")
            data = cast(TemplateGenerationPayload, loaded)
            parameters = data["parameters"]
            for key in ("users", "projects"):
                if key in parameters:
                    parameters[key] = tuple(parameters[key])
            result = _use_case().execute(
                GenerateDocumentCommand(
                    template_type=data["template_type"],
                    template_id=data.get("template_id"),
                    is_pdf=data["is_pdf"],
                    parameters=GenerationParameters(**parameters),
                )
            )
        except ValidationError as error:
            return {"msg": "Некорректные данные", "errors": error.messages}, 400
        except ValueError as error:
            return {"msg": str(error)}, 400
        except TemplateNotFoundError:
            return {"msg": "Template not found"}, 404
        except TemplateStorageError:
            logger.exception("Template storage request failed during generation")
            return {"msg": "Хранилище шаблонов недоступно"}, 503
        except TemplateGenerationError:
            logger.exception("Template generation failed")
            return {"msg": "Ошибка при генерации файла"}, 500
        response = Response(
            result.chunks,
            headers={
                "Content-Type": result.content_type,
                "Content-Disposition": result.content_disposition,
            },
        )
        response.call_on_close(result.close)
        return response
