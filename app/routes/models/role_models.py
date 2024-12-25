from flask_restx import fields, Model, reqparse


# Модель для одной роли
role_model = Model('Role', {
    'role_id': fields.String(required=True, description='Идентификатор роли.'),
    'name': fields.String(required=True, description='Название роли.')
})


# Модель для ответа с данными нескольких ролей
role_all_response = Model('RolesAllResponse', {
    'msg': fields.String(required=True, description='Сообщение.'),
    'roles': fields.List(fields.Nested(role_model), description='Список ролей.')
})

# Парсер для фильтрации, сортировки и пагинации
role_filter_parser = reqparse.RequestParser()
role_filter_parser.add_argument(
    'offset', type=int, required=False, default=0, help='Смещение для пагинации.')
role_filter_parser.add_argument(
    'limit', type=int, required=False, default=10, help='Лимит записей.')
role_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Поле для сортировки.')
role_filter_parser.add_argument(
    'sort_order', type=str, required=False, choices=['asc', 'desc'], help='Порядок сортировки.')
role_filter_parser.add_argument(
    'role_id', type=str, required=False, help='Фильтр по идентификатору роли.')
role_filter_parser.add_argument(
    'name', type=str, required=False, help='Фильтр по названию роли.')
