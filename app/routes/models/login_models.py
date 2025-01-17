from flask_restx import fields, Model
from app.utils.helpers import generate_swagger_model
from app.schemas.login_schemas import LoginSchema, RefreshTokenSchema

# Определение модели для логина
login_model = generate_swagger_model(
    LoginSchema(), "Login")

# Определение модели для обновления токена
refresh_model = generate_swagger_model(
    RefreshTokenSchema(), "RefreshToken")

# Определение модели ответа сервера
response_auth = Model('Tokens', {
    'access_token': fields.String(description='Access token for user'),
    'refresh_token': fields.String(description='Refresh token for user'),
    'msg': fields.String(required=True, description='Message'),
    'user_id': fields.String(description='ID of user')
})
