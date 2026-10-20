from copy import deepcopy
from typing import Any

from marshmallow import Schema, fields, validate

from app.domain.templates import TemplateTypes
from app.schemas.template_data_schemas import template_data_schema
from app.use_cases.templates.parameters import TemplateParameters


def _object_schema(schema: Schema, title: str) -> dict[str, Any]:
    properties = {
        name: _field_schema(field, str(field.metadata.get("title", name)))
        for name, field in schema.fields.items()
        if not field.load_only
    }
    return {
        "type": "object",
        "title": title,
        "properties": properties,
        "additionalProperties": False,
        "required": [
            name
            for name, field in schema.fields.items()
            if field.required and not field.load_only
        ],
        "example": {
            name: deepcopy(value["example"]) for name, value in properties.items()
        },
    }


def _field_schema(field: fields.Field, title: str) -> dict[str, Any]:
    result: dict[str, Any]
    if isinstance(field, fields.Nested):
        result = _object_schema(field.schema, title)
    elif isinstance(field, fields.List):
        item = _field_schema(field.inner, f"{title}: элемент")
        result = {
            "type": "array",
            "title": title,
            "items": item,
            "example": [deepcopy(item["example"])],
        }
    else:
        result = {"title": title}
        if isinstance(field, fields.UUID):
            result.update(type="string", format="uuid")
        elif isinstance(field, fields.Date):
            result.update(type="string", format="date")
        elif isinstance(field, fields.Boolean):
            result["type"] = "boolean"
        elif isinstance(field, fields.Integer):
            result["type"] = "integer"
        elif isinstance(field, (fields.Float, fields.Decimal)):
            result["type"] = "number"
        elif isinstance(field, fields.String):
            result["type"] = "string"
        else:
            raise TypeError(f"Unsupported template field: {type(field).__name__}")
        result["example"] = deepcopy(field.metadata.get("example"))
    for validator in field.validators:
        if isinstance(validator, validate.Range):
            if validator.min is not None:
                result["minimum" if validator.min_inclusive else "exclusiveMinimum"] = (
                    validator.min
                )
            if validator.max is not None:
                result["maximum" if validator.max_inclusive else "exclusiveMaximum"] = (
                    validator.max
                )
        elif isinstance(validator, validate.OneOf):
            result["enum"] = list(validator.choices)
    if field.allow_none:
        result["type"] = [result["type"], "null"]
        if "enum" in result:
            result["enum"].append(None)
    return result


def _has_type(schema: dict[str, Any], expected: str) -> bool:
    value = schema.get("type")
    return value == expected or isinstance(value, list) and expected in value


def _paths(schema: dict[str, Any], prefix: str = "") -> list[str]:
    paths = []
    for name, child in schema.get("properties", {}).items():
        path = f"{prefix}.{name}" if prefix else name
        paths.append(path)
        if _has_type(child, "array"):
            paths.extend(_paths(child["items"], f"{path}[i]"))
        else:
            paths.extend(_paths(child, path))
    return paths


def _add_array_aliases(schema: dict[str, Any]) -> None:
    properties = schema.get("properties", {})
    for name, child in list(properties.items()):
        if _has_type(child, "array"):
            _add_array_aliases(child["items"])
            properties[f"{name}[i]"] = deepcopy(child["items"])
        else:
            _add_array_aliases(child)


class MarshmallowTemplateParametersProvider:
    def describe(self, template_type: TemplateTypes) -> TemplateParameters:
        schema = _object_schema(
            template_data_schema(template_type), template_type.label()
        )
        paths = _paths(schema)
        _add_array_aliases(schema)
        return TemplateParameters(template_type, paths, schema)
