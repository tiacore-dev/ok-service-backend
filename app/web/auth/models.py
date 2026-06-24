from flask_restx import Model, fields

from app.schemas.login_schemas import LoginSchema, RefreshTokenSchema
from app.utils.helpers import generate_swagger_model

login_model = generate_swagger_model(LoginSchema(), "Login")
refresh_model = generate_swagger_model(RefreshTokenSchema(), "RefreshToken")

hello_model = Model(
    "HelloMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
    },
)

response_auth = Model(
    "Tokens",
    {
        "access_token": fields.String(description="Access token for user"),
        "refresh_token": fields.String(description="Refresh token for user"),
        "msg": fields.String(required=True, description="Message"),
        "user_id": fields.String(description="ID of user"),
    },
)
