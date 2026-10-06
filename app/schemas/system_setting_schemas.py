from marshmallow import Schema, ValidationError, fields, validates_schema


class SystemSettingEditSchema(Schema):
    value = fields.String(required=False, allow_none=True)
    name = fields.String(required=False, allow_none=False)

    @validates_schema
    def validate_at_least_one_field(self, data, **kwargs):
        if not data:
            raise ValidationError("At least one of 'value' or 'name' is required.")
