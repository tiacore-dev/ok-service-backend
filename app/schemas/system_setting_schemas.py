from marshmallow import Schema, fields


class SystemSettingEditSchema(Schema):
    value = fields.String(required=True, allow_none=True)
