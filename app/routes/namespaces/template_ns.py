import json
import logging
from io import BytesIO

import requests
from flask import current_app, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError

from app.routes.models.template_models import template_generate_model
from app.schemas.template_schemas import TemplateGenerateSchema

logger = logging.getLogger("ok_service")

template_ns = Namespace("templates", description="template management operations")

template_ns.models[template_generate_model.name] = template_generate_model


@template_ns.route("/generate")
class templateAdd(Resource):
    @jwt_required()
    @template_ns.expect(template_generate_model)
    @template_ns.response(400, "Bad request, invalid data.")
    @template_ns.response(500, "Internal Server Error")
    @template_ns.doc(description="Генерация файла по шаблону")
    @template_ns.response(
        201,
        "Файл успешно сгенерирован",
        headers={
            "Content-Disposition": 'attachment; filename="yourfile.docx"',
            "Content-Type": """application/vnd.openxmlformats-officedocument.
            wordprocessingml.document""",
        },
    )
    def post(self):
        current_user = json.loads(get_jwt_identity())
        schema = TemplateGenerateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            logger.error(
                f"Ошибка валидации при добавлении пользователя: {err.messages}",
                extra={"login": current_user.get("login")},
            )
            return {"msg": "Некорректные данные", "errors": err.messages}, 400
        template_url = current_app.config.get("TEMPLATE_SERVICE_URL")
        response = requests.post(url=template_url, json=data)
        if not response.ok:
            logger.error(
                f"Ошибка от TEMPLATE_SERVICE: {response.status_code} - {response.text}"
            )
            return {"msg": "Ошибка при генерации файла"}, 500
        document_bytes = response.content
        return send_file(
            BytesIO(document_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name="output.docx",
        )
