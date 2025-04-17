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
    "night_shift_available": fields.Boolean(required=True, description="If night shifts are available"),
    "extreme_conditions_available": fields.Boolean(required=True, description="If extreme conditions are available"),
    "created_at": fields.Integer(required=True, description="Date project was created at"),
    "created_by": fields.String(required=True, description="Creator of project"),
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

project_stats_model = Model('ProjectStats', {
    "project_work_quantity": fields.Float(required=True),
    "shift_report_details_quantity": fields.Float(required=True),
    "project_work_name": fields.String(required=False),
})


project_stats_response = Model('ProjectStatsResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "stats": fields.Raw(required=True, description="Dict of work_id -> stat")
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
    'night_shift_available',
    # Интерпретация значения как логического
    type=lambda x: x.lower() in ['true', '1'],
    required=False,
    help="Флаг для фильтрации по удаленным отчетам"
)
project_filter_parser.add_argument(
    'extreme_conditions_available',
    # Интерпретация значения как логического
    type=lambda x: x.lower() in ['true', '1'],
    required=False,
    help="Флаг для фильтрации по удаленным отчетам"
)
project_filter_parser.add_argument(
    'deleted',
    # Интерпретация значения как логического
    type=lambda x: x.lower() in ['true', '1'],
    required=False,
    help="Флаг для фильтрации по удаленным отчетам"
)
