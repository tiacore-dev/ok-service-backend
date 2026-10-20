from marshmallow import Schema, ValidationError, fields, validates_schema

from app.domain.templates import TemplateTypes
from app.schemas.template_data_schemas import (
    ObjectReportRequestSchema,
    PayrollRequestSchema,
)


class ShiftReportParametersSchema(Schema):
    shift_report_id = fields.UUID(required=True)


class TemplateGenerateSchema(Schema):
    template_type = fields.Enum(TemplateTypes, by_value=True, required=True)
    template_id = fields.UUID()
    is_pdf = fields.Boolean(allow_none=True, load_default=None)
    parameters = fields.Dict(keys=fields.String(), load_default=dict)

    @validates_schema
    def validate_parameters(self, data, **kwargs):
        kind = data["template_type"]
        schemas = {
            TemplateTypes.WORK_TYPES: Schema,
            TemplateTypes.SHIFT_REPORT: ShiftReportParametersSchema,
            TemplateTypes.SHIFT_REPORT_LIST: ObjectReportRequestSchema,
            TemplateTypes.PAYROLL: PayrollRequestSchema,
            TemplateTypes.OBJECT_REPORT: ObjectReportRequestSchema,
        }
        try:
            data["parameters"] = schemas[kind]().load(data["parameters"])
        except ValidationError as error:
            raise ValidationError({"parameters": error.messages}) from error
