from flask_restx import Model, fields, reqparse

# Модель для создания проекта
project_create_model = Model('ProjectCreate', {
    "name": fields.String(required=True, description="Name of the project"),
    "object": fields.String(required=True, description="Object ID associated with the project"),
    "project_leader": fields.String(required=False, description="User ID of the project leader")
})

# Модель для объекта проекта
object_model = Model('Object', {
    "object_id": fields.String(required=True, description="ID of the object"),
    "name": fields.String(required=True, description="Name of the object"),
    "address": fields.String(required=False, description="Address of the object"),
    "description": fields.String(required=False, description="Description of the object"),
    "status": fields.String(required=False, description="Status ID of the object"),
    "deleted": fields.Boolean(required=True, description="Deletion status")
})

# Модель для лидера проекта
user_model = Model('User', {
    "user_id": fields.String(required=True, description="ID of the user"),
    "login": fields.String(required=True, description="Login of the user"),
    "name": fields.String(required=True, description="Name of the user"),
    "role": fields.String(required=True, description="Role of the user"),
    "category": fields.Integer(required=False, description="Category of the user"),
    "deleted": fields.Boolean(required=True, description="Deletion status")
})

# Модель для проекта с вложенными данными
project_model = Model('Project', {
    "project_id": fields.String(required=True, description="ID of the project"),
    "name": fields.String(required=True, description="Name of the project"),
    "object": fields.Nested(object_model, required=True, description="Object data associated with the project"),
    "project_leader": fields.Nested(user_model, required=False, description="User data of the project leader"),
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
