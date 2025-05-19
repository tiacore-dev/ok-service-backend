from flask_restx import Model, fields, reqparse
from app.schemas.work_schemas import WorkCreateSchema
from app.utils.helpers import generate_swagger_model
from app.routes.models.work_category_models import work_category_model
from app.routes.models.work_price_models import work_price_model

# Модель для создания проекта
work_create_model = generate_swagger_model(
    WorkCreateSchema(), "WorkCreate")


# Модель для объекта работы
work_model = Model('Work', {
    "work_id": fields.String(required=True, description="ID of the work"),
    "name": fields.String(required=True, description="Name of the work"),
    "category": fields.Nested(work_category_model, description="Work category data"),
    "measurement_unit": fields.String(required=False, description="Measurement unit of the work"),
    "created_at": fields.Integer(required=True, description="Date work was created at"),
    "created_by": fields.String(required=True, description="Creator of work"),
    "deleted": fields.Boolean(required=True, description="Deletion status"),
    "work_prices": fields.List(fields.Nested(work_price_model), required=False, description="List of prices")
})

# Модель для сообщений
work_msg_model = Model('WorkMessage', {
    "msg": fields.String(required=True, description="Response message"),
    "work_id": fields.String(description="ID of work")
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
    'deleted', type=lambda x: x.lower() in ['true', '1'], help="Filter by deletion status")
work_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Field for sorting'
)
work_filter_parser.add_argument(
    'sort_order', type=str, required=False, choices=['asc', 'desc'], help='Order of sorting'
)
