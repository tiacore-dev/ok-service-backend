from flask_restx import fields, Model
from marshmallow import Schema, fields as ma_fields

# 🔹 Глобальный реестр моделей, чтобы не дублировать
registered_models = {}

# 🔹 Фиксированный маппинг типов
type_mapping = {
    ma_fields.String: fields.String,
    ma_fields.Integer: fields.Integer,
    ma_fields.Float: fields.Float,
    ma_fields.Boolean: fields.Boolean,
    ma_fields.UUID: fields.String,  # UUID храним как строку
    # Dict маппится в Raw (универсальный тип Flask-RESTx)
    ma_fields.Dict: fields.Raw,

}


def map_field(field_obj):
    """Функция маппинга типов Marshmallow → Flask-RESTx"""
    field_type = type(field_obj)

    if field_type == ma_fields.List:
        inner_type = map_field(field_obj.inner)
        return fields.List(inner_type)

    if field_type == ma_fields.Nested:
        nested_schema = field_obj.nested

        if isinstance(nested_schema, type) and issubclass(nested_schema, Schema):
            nested_schema = nested_schema()

        # 🔥 Исправлено: Используем ЕДИНОЕ имя модели
        nested_model_name = nested_schema.__class__.__name__.replace(
            "Schema", "")

        # ✅ Если модель уже зарегистрирована, возвращаем ее!
        if nested_model_name in registered_models:
            # print(f"⚠️ Используем уже зарегистрированную модель: {
            #      nested_model_name}")
            return fields.Nested(registered_models[nested_model_name])

        # ❗️ Если модели нет, создаем новую
        nested_model = generate_swagger_model(nested_schema, nested_model_name)
        return fields.Nested(nested_model)

    return type_mapping.get(field_type, fields.String)()


def generate_swagger_model(schema: Schema, name: str) -> Model:
    """Генерация Flask-RESTx Model из Marshmallow Schema"""

    # Если передан класс, создаем экземпляр
    if isinstance(schema, type) and issubclass(schema, Schema):
        schema = schema()

    # 🔥 Исправлено: Имя модели всегда без "Schema"
    fixed_name = name.replace("Schema", "")

    # ✅ Проверяем, есть ли такая модель в реестре
    if fixed_name in registered_models:
        # print(f"⚠️ Используем уже созданную модель: {fixed_name}")
        return registered_models[fixed_name]

    model_fields = {}

    for field_name, field_obj in schema.fields.items():
        model_fields[field_name] = map_field(field_obj)

    model = Model(fixed_name, model_fields)
    registered_models[fixed_name] = model  # Сохраняем в реестр
    # print(f"✅ Создана модель {fixed_name} с полями: {
    #      list(model_fields.keys())}")

    return model
