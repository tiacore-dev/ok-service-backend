from marshmallow import Schema, fields


class LoginSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля
    login = fields.String(required=True, error_messages={
                          "required": "Field 'login' is required."})
    password = fields.String(required=True, error_messages={
                             "required": "Field 'password' is required."})


class RefreshTokenSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля
    refresh_token = fields.String(required=True, error_messages={
                                  "required": "Field 'refresh_token' is required."})
