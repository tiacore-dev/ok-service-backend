from flask_restx import fields, Model, reqparse

# Модель для создания статуса объекта
object_status_create_model = Model('ObjectStatusCreate', {
    'name': fields.String(required=True, description='Название статуса объекта.')
})

# Модель для одного статуса объекта
object_status_model = Model('ObjectStatus', {
    'object_status_id': fields.String(required=True, description='Идентификатор статуса объекта.'),
    'name': fields.String(required=True, description='Название статуса объекта.')
})

# Модель для ответа при успешных действиях
object_status_msg_model = Model('ObjectStatusMessage', {
    'msg': fields.String(required=True, description='Сообщение.')
})

# Модель для ответа с данными одного статуса объекта
object_status_response = Model('ObjectStatusResponse', {
    'msg': fields.String(required=True, description='Сообщение.'),
    'object_status': fields.Nested(object_status_model, required=True, description='Данные о статусе объекта.')
})

# Модель для ответа с данными нескольких статусов объектов
object_status_all_response = Model('ObjectStatusAllResponse', {
    'msg': fields.String(required=True, description='Сообщение.'),
    'object_statuses': fields.List(fields.Nested(object_status_model), description='Список статусов объектов.')
})

# Парсер для фильтрации, сортировки и пагинации
object_status_filter_parser = reqparse.RequestParser()
object_status_filter_parser.add_argument(
    'offset', type=int, required=False, default=0, help='Смещение для пагинации.')
object_status_filter_parser.add_argument(
    'limit', type=int, required=False, default=10, help='Лимит записей.')
object_status_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Поле для сортировки.')
object_status_filter_parser.add_argument(
    'sort_order', type=str, required=False, choices=['asc', 'desc'], help='Порядок сортировки.')
object_status_filter_parser.add_argument(
    'object_status_id', type=str, required=False, help='Фильтр по идентификатору статуса объекта.')
object_status_filter_parser.add_argument(
    'name', type=str, required=False, help='Фильтр по названию статуса объекта.')
