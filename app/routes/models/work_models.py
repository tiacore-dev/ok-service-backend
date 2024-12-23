from flask_restx import Model, fields, reqparse

# Модель для создания работы
work_create_model = Model('WorkCreate', {
    "name": fields.String(required=True, description="Name of the work"),
    "category": fields.String(required=False, description="Work category ID"),
    "measurement_unit": fields.String(required=False, description="Measurement unit of the work")
})

# Модель для объекта работы
work_model = Model('Work', {
    "work_id": fields.String(required=True, description="ID of the work"),
    "name": fields.String(required=True, description="Name of the work"),
    "category": fields.String(required=False, description="Work category data"),
    "measurement_unit": fields.String(required=False, description="Measurement unit of the work"),
    "deleted": fields.Boolean(required=True, description="Deletion status")
})

# Модель для сообщений
work_msg_model = Model('WorkMessage', {
    "msg": fields.String(required=True, description="Response message")
})

# Модель для ответа с одной работой
work_response = Model('WorkResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "work": fields.Nested(work_model, required=True)
})

# Модель для ответа со списком работ
work_all_response = Model('WorkAllResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "works": fields.List(fields.Nested(work_model), description="List of works")
})

# Парсер для фильтрации, сортировки и пагинации
work_filter_parser = reqparse.RequestParser()
work_filter_parser.add_argument(
    'offset', type=int, default=0, help="Offset for pagination"
)
work_filter_parser.add_argument(
    'limit', type=int, default=10, help="Limit for pagination"
)
work_filter_parser.add_argument('name', type=str, help="Filter by name")
work_filter_parser.add_argument(
    'deleted', type=bool, help="Filter by deletion status")
work_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Field for sorting'
)
work_filter_parser.add_argument(
    'sort_order', type=str, required=False, choices=['asc', 'desc'], help='Order of sorting'
)
