from flask_restx import Model, fields, reqparse
from app.schemas.project_work_schemas import ProjectWorkCreateSchema
from app.utils.helpers import generate_swagger_model

# Модель для создания проекта
project_work_create_model = generate_swagger_model(
    ProjectWorkCreateSchema(), "ProjectWorkCreate")


# Модель для ProjectWork
project_work_model = Model('ProjectWork', {
    "project_work_id": fields.String(required=True, description="ID of the project work"),
    "project": fields.String(required=True, description="Project data associated with the project work"),
    "work": fields.String(required=True, description="Work data associated with the project work"),
    "quantity": fields.Float(required=True, description="Quantity of the work"),
    "summ": fields.Float(required=False, description="Sum of the project work"),
    "signed": fields.Boolean(required=True, description="If the project work is signed")
})


# Модели для сообщений и ответов
project_work_msg_model = Model('ProjectWorkMessage', {
    "msg": fields.String(required=True, description="Response message")
})

project_work_response = Model('ProjectWorkResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "project_work": fields.Nested(project_work_model, required=True)
})

project_work_all_response = Model('ProjectWorkAllResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "project_works": fields.List(fields.Nested(project_work_model), description="List of project works")
})

# Парсер для фильтрации и пагинации
project_work_filter_parser = reqparse.RequestParser()
project_work_filter_parser.add_argument(
    'offset', type=int, default=0, help="Offset for pagination"
)
project_work_filter_parser.add_argument(
    'limit', type=int, default=10, help="Limit for pagination"
)
project_work_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Field for sorting'
)
project_work_filter_parser.add_argument(
    'sort_order', type=str, required=False, choices=['asc', 'desc'], help='Order of sorting'
)
project_work_filter_parser.add_argument(
    'signed', type=lambda x: x.lower() in ['true', '1'], required=False, help='Filter by signed status'
)
project_work_filter_parser.add_argument(
    'work', type=str, required=False, help="Filter by work ID"
)
project_work_filter_parser.add_argument(
    'project', type=str, required=False, help="Filter by project ID"
)
project_work_filter_parser.add_argument(
    'min_quantity', type=float, required=False, help="Minimum quantity filter"
)
project_work_filter_parser.add_argument(
    'max_quantity', type=float, required=False, help="Maximum quantity filter"
)
project_work_filter_parser.add_argument(
    'min_summ', type=float, required=False, help="Minimum summ filter"
)
project_work_filter_parser.add_argument(
    'max_summ', type=float, required=False, help="Maximum summ filter"
)
