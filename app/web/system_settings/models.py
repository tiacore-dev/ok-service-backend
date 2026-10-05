from flask_restx import Model, fields

system_setting_model = Model(
    "SystemSetting",
    {
        "system_setting_id": fields.String(required=True),
        "value": fields.String(required=False, allow_none=True),
        "modified_at": fields.Integer(required=False, allow_none=True),
        "modified_by": fields.String(required=False, allow_none=True),
    },
)
system_setting_response = Model(
    "SystemSettingResponse",
    {
        "msg": fields.String(required=True),
        "system_setting": fields.Nested(system_setting_model, required=True),
    },
)
system_setting_all_response = Model(
    "SystemSettingAllResponse",
    {
        "msg": fields.String(required=True),
        "system_settings": fields.List(fields.Nested(system_setting_model)),
    },
)
system_setting_edit_model = Model(
    "SystemSettingEdit",
    {"value": fields.String(required=True, allow_none=True)},
)
