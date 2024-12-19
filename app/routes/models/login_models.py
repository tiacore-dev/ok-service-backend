from flask_restx import fields, Model

# Определение модели для логина
login_model = Model('Login', {
    'login': fields.String(required=True, description='Username for login'),
    'password': fields.String(required=True, description='Password for login')
})

# Определение модели для обновления токена
refresh_model = Model('RefreshToken', {
    'refresh_token': fields.String(required=True, description='Refresh token for renewing access token')
})

response_auth = Model('Tokens', {
    'access_token': fields.String(required=True, description='Access token for user'),
    'refresh_token': fields.String(required=True, description='Refresh token for user')
})
