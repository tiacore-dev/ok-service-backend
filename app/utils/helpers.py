from flask_restx import Model, fields


def generate_swagger_model(schema, name):
    """Генерация Swagger модели из Marshmallow схемы."""
    return Model(
        name,
        {field: fields.String(description=str(schema.fields[field].metadata.get("description", "")))
         for field in schema.fields}
    )
