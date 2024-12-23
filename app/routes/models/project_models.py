from flask_restx import Model, fields, reqparse

# Модель для создания проекта
project_create_model = Model('ProjectCreate', {
    "name": fields.String(required=True, description="Name of the project"),
    "object": fields.String(required=True, description="Object ID associated with the project"),
    "project_leader": fields.String(required=False, description="User ID of the project leader")
})

# Модель для объекта проекта
project_model = Model('Project', {
    "project_id": fields.String(required=True, description="ID of the project"),
    "name": fields.String(required=True, description="Name of the project"),
    "object": fields.String(required=True, description="Object data associated with the project"),
    "project_leader": fields.String(required=False, description="Project leader's data"),
    "deleted": fields.Boolean(required=True, description="Deletion status")
})

# Модель для сообщений
project_msg_model = Model('ProjectMessage', {
    "msg": fields.String(required=True, description="Response message")
})

# Модель для ответа с одним проектом
project_response = Model('ProjectResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "project": fields.Nested(project_model, required=True)
})

# Модель для ответа со списком проектов
project_all_response = Model('ProjectAllResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "projects": fields.List(fields.Nested(project_model), description="List of projects")
})

# Парсер для фильтрации и пагинации
project_filter_parser = reqparse.RequestParser()
project_filter_parser.add_argument(
    'offset', type=int, default=0, help="Offset for pagination"
)
project_filter_parser.add_argument(
    'limit', type=int, default=10, help="Limit for pagination"
)
project_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Поле для сортировки')
project_filter_parser.add_argument('sort_order', type=str, required=False, choices=[
    'asc', 'desc'], help='Порядок сортировки')
project_filter_parser.add_argument('name', type=str, help="Filter by name")
project_filter_parser.add_argument(
    'deleted', type=bool, help="Filter by deletion status"
)
