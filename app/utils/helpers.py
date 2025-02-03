from flask_restx import fields, Model
from marshmallow import Schema, fields as ma_fields

# Маппинг типов Marshmallow -> flask-restx
type_mapping = {
    ma_fields.String: fields.String,
    ma_fields.Integer: fields.Integer,
    ma_fields.Float: fields.Float,
    ma_fields.Boolean: fields.Boolean,
    ma_fields.UUID: fields.String,  # UUID храним как строку
}


def generate_swagger_model(schema: Schema, name: str) -> Model:
    """Генерация Swagger модели из Marshmallow схемы с сохранением типов."""
    model_fields = {}

    for field_name, field_obj in schema.fields.items():
        field_type = type(field_obj)

        # Если тип есть в маппинге, используем его
        flask_restx_field = type_mapping.get(field_type, fields.String)

        # Создаем поле со Swagger-описанием
        model_fields[field_name] = flask_restx_field(
            description=str(field_obj.metadata.get("description", ""))
        )

    return Model(name, model_fields)
