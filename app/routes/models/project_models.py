from flask_restx import Model, fields, reqparse
from app.schemas.project_schemas import ProjectCreateSchema
from app.utils.helpers import generate_swagger_model

# Модель для создания проекта
project_create_model = generate_swagger_model(
    ProjectCreateSchema(), "ProjectCreate")


# Модель для проекта с вложенными данными
project_model = Model('Project', {
    "project_id": fields.String(required=True, description="ID of the project"),
    "name": fields.String(required=True, description="Name of the project"),
    "object": fields.String(required=True, description="Object data associated with the project"),
    "project_leader": fields.String(required=False, description="User data of the project leader"),
    "deleted": fields.Boolean(required=True, description="Deletion status")
})


# Модель для сообщений
project_msg_model = Model('ProjectMessage', {
    "msg": fields.String(required=True, description="Response message"),
    "project_id": fields.String(description="ID of project")
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
project_filter_parser.add_argument(
    'object', type=str, required=False, help="Filter by object ID"
)
project_filter_parser.add_argument(
    'project_leader', type=str, required=False, help="Filter by project leader ID"
)
project_filter_parser.add_argument('name', type=str, help="Filter by name")
project_filter_parser.add_argument(
    'deleted',
    # Интерпретация значения как логического
    type=lambda x: x.lower() in ['true', '1'],
    required=False,
    help="Флаг для фильтрации по удаленным отчетам"
)
