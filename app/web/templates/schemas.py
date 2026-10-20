from marshmallow import Schema, fields, validate

from app.domain.templates import TemplateTypes


class TemplateEditSchema(Schema):
    name = fields.String(validate=validate.Length(min=1, max=255))
    description = fields.String(allow_none=True)
    output_file_name = fields.String(allow_none=True)
    is_horizontal = fields.Boolean()
    is_pdf = fields.Boolean()
    is_default = fields.Boolean()


class TemplateCreateSchema(TemplateEditSchema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    template_type = fields.Enum(TemplateTypes, by_value=True, required=True)


class TemplateFilterSchema(Schema):
    template_type = fields.Enum(TemplateTypes, by_value=True)
    offset = fields.Integer(load_default=0, validate=validate.Range(min=0))
    limit = fields.Integer(load_default=100, validate=validate.Range(min=1, max=1000))


class TemplateParamsQuerySchema(Schema):
    template_type = fields.Enum(TemplateTypes, by_value=True, required=True)
