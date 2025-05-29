from marshmallow import EXCLUDE, Schema, ValidationError, fields, validates_schema


class TemplateGenerateSchema(Schema):
    class Meta:
        unknown = EXCLUDE  # игнорировать лишние поля

    url = fields.String(required=False, allow_none=True)
    file_name = fields.String(required=False, allow_none=True)
    name = fields.String(
        required=True, error_messages={"required": "Field 'name' is required."}
    )
    is_pdf = fields.Boolean(missing=False)
    document_data = fields.Dict(required=True)

    @validates_schema
    def validate_url_or_file_name(self, data, **kwargs):
        if not data.get("url") and not data.get("file_name"):
            raise ValidationError(
                "Должно быть указано либо 'url', либо 'file_name'", field_name="url"
            )
