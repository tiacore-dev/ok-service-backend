from marshmallow import Schema
from app.utils.helpers import generate_swagger_model


def crud_models(schema: Schema, name: str):
    return generate_swagger_model(schema, name)
