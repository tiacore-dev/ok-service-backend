from flask_restx import reqparse
from flask_restx import fields, Model


# Определение модели для логина
user_create_model = Model('UserCreate', {
    'login': fields.String(required=True, description='Логин пользователя.'),
    'password': fields.String(required=True, description='Пароль пользователя.'),
    "name": fields.String(required=True, description='Имя пользователя.'),
    "role": fields.String(required=True, description='Роль пользователя.'),
    "category": fields.Integer(required=False, description='Категория.'),
})

user_model = Model('User', {
    "user_id": fields.String(required=True, description='ID пользователя'),
    'login': fields.String(required=True, description='Логин пользователя.'),
    "name": fields.String(required=True, description='Имя пользователя.'),
    "role": fields.String(required=True, description='Роль пользователя.'),
    "category": fields.Integer(required=False, description='Категория.'),
    "deleted": fields.Boolean(required=True, description='Удален ли пользователь.')
})

# Модель для ответа
user_all_response = Model('UserResponse', {
    'msg': fields.String(description='Сообщение'),
    'users': fields.List(fields.Nested(user_model), description='Список пользователей'),
})

# Определение модели для обновления токена
user_msg_model = Model('RefreshToken', {
    'msg': fields.String(required=True, description='Сообщение.')
})

user_response = Model('Tokens', {
    'msg': fields.String(required=True, description='Сообщение.'),
    'user': fields.Nested(user_model, required=True, description='Данные о пользователе.')
})


# Создаем парсер для входных параметров
user_filter_parser = reqparse.RequestParser()
user_filter_parser.add_argument(
    'offset', type=int, required=False, default=0, help='Смещение для пагинации')
user_filter_parser.add_argument(
    'limit', type=int, required=False, default=10, help='Лимит записей')
user_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Поле для сортировки')
user_filter_parser.add_argument('sort_order', type=str, required=False, choices=[
                                'asc', 'desc'], help='Порядок сортировки')
user_filter_parser.add_argument(
    'login', type=str, required=False, help='Фильтр по логину')
user_filter_parser.add_argument(
    'name', type=str, required=False, help='Фильтр по имени')
user_filter_parser.add_argument(
    'role', type=str, required=False, help='Фильтр по роли')
user_filter_parser.add_argument(
    'category', type=int, required=False, help='Фильтр по категории')
user_filter_parser.add_argument(
    'deleted', type=bool, required=False, help='Фильтр по удаленному статусу')
