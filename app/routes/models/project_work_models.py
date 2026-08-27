from flask_restx import Model, fields, reqparse

from app.schemas.project_work_schemas import (
    ProjectWorkCreateSchema,
    ProjectWorkEditSchema,
)
from app.utils.helpers import generate_swagger_model

# Модель для создания проекта
project_work_create_model = generate_swagger_model(
    ProjectWorkCreateSchema(), "ProjectWorkCreate"
)

project_work_edit_model = generate_swagger_model(
    ProjectWorkEditSchema(), "ProjectWorkEdit"
)


# Модель для ProjectWork
project_work_model = Model(
    "ProjectWork",
    {
        "project_work_id": fields.String(
            required=True, description="ID of the project work"
        ),
        "project_work_name": fields.String(
            required=False, description="Name of the projet work"
        ),
        "project": fields.String(
            required=True, description="Project data associated with the project work"
        ),
        "work": fields.String(
            required=True, description="Work data associated with the project work"
        ),
        "quantity": fields.Float(required=True, description="Quantity of the work"),
        "price": fields.Float(required=False, description="Price per unit of work"),
        "summ": fields.Float(required=False, description="Sum of the project work"),
        "created_at": fields.Integer(
            required=True,
            description="Unix epoch milliseconds: project work creation time",
        ),
        "created_by": fields.String(
            required=True, description="Creator of project work"
        ),
        "signed": fields.Boolean(
            required=True, description="If the project work is signed"
        ),
        "project_work_quantity": fields.Float(required=False),
        "shift_report_details_quantity": fields.Float(required=False),
        "acceptance_status": fields.String(
            required=False, enum=["not_checked", "partial", "accepted"]
        ),
    },
)


# Модели для сообщений и ответов
project_work_msg_model = Model(
    "ProjectWorkMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
        "project_work_id": fields.String(description="ID of project work"),
    },
)

project_work_msg_many_model = Model(
    "ProjectWorkManyMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
        "project_work_ids": fields.List(
            fields.String(), description="List of project work IDs"
        ),
    },
)

project_work_response = Model(
    "ProjectWorkResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "project_work": fields.Nested(project_work_model, required=True),
    },
)

project_work_all_response = Model(
    "ProjectWorkAllResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "project_works": fields.List(
            fields.Nested(project_work_model), description="List of project works"
        ),
    },
)

# Парсер для фильтрации и пагинации
project_work_filter_parser = reqparse.RequestParser()
project_work_filter_parser.add_argument(
    "offset", type=int, default=0, help="Offset for pagination"
)
project_work_filter_parser.add_argument(
    "limit", type=int, default=1000, help="Limit for pagination"
)
project_work_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Field for sorting"
)
project_work_filter_parser.add_argument(
    "sort_order",
    type=str,
    required=False,
    choices=["asc", "desc"],
    help="Order of sorting",
)
project_work_filter_parser.add_argument(
    "signed",
    type=lambda x: x.lower() in ["true", "1"],
    required=False,
    help="Filter by signed status",
)
project_work_filter_parser.add_argument(
    "work", type=str, required=False, help="Filter by work ID"
)
project_work_filter_parser.add_argument(
    "project", type=str, required=False, help="Filter by project ID"
)
project_work_filter_parser.add_argument(
    "project_work_name", type=str, required=False, help="Filter by project work name"
)
project_work_filter_parser.add_argument(
    "min_quantity", type=float, required=False, help="Minimum quantity filter"
)
project_work_filter_parser.add_argument(
    "max_quantity", type=float, required=False, help="Maximum quantity filter"
)
project_work_filter_parser.add_argument(
    "min_summ", type=float, required=False, help="Minimum summ filter"
)
project_work_filter_parser.add_argument(
    "max_summ", type=float, required=False, help="Maximum summ filter"
)
project_work_filter_parser.add_argument(
    "with_stat",
    type=lambda x: x.lower() in ["true", "1"],
    required=False,
    default=False,
    help="Include cached project-work statistics",
)
