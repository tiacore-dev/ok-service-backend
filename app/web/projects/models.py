from flask_restx import Model, fields, reqparse

from app.schemas.project_schemas import ProjectCreateSchema, ProjectEditSchema
from app.utils.helpers import generate_swagger_model
from app.routes.models.place_models import place_model

project_create_model = generate_swagger_model(ProjectCreateSchema(), "ProjectCreate")
project_edit_model = generate_swagger_model(ProjectEditSchema(), "ProjectEdit")

project_model = Model(
    "Project",
    {
        "project_id": fields.String(required=False, description="ID of the project"),
        "name": fields.String(required=False, description="Name of the project; may be null in legacy records"),
        "object": fields.String(required=False, description="Object data associated with the project; may be null in legacy records"),
        "project_leader": fields.String(required=False, description="User data of the project leader"),
        "night_shift_available": fields.Boolean(required=False, description="If night shifts are available"),
        "extreme_conditions_available": fields.Boolean(required=False, description="If extreme conditions are available"),
        "created_at": fields.Integer(required=False, description="Unix epoch milliseconds: project creation time"),
        "created_by": fields.String(required=False, description="Creator of project"),
        "deleted": fields.Boolean(required=False, description="Deletion status"),
    },
)

project_msg_model = Model(
    "ProjectMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
        "project_id": fields.String(description="ID of project"),
    },
)

project_view_model = Model("ProjectView", {**project_model, "places": fields.List(fields.Nested(place_model), required=True)})

project_response = Model(
    "ProjectResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "project": fields.Nested(project_view_model, required=True),
    },
)

project_all_response = Model(
    "ProjectAllResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "projects": fields.List(fields.Nested(project_model), description="List of projects"),
    },
)

project_stats_model = Model(
    "ProjectStats",
    {
        "project_work_quantity": fields.Float(required=True),
        "shift_report_details_quantity": fields.Float(required=True),
        "project_work_name": fields.String(required=False),
    },
)

project_stats_response = Model(
    "ProjectStatsResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "stats": fields.Raw(required=True, description="Dict of work_id or project_work_id -> stat"),
    },
)

project_filter_parser = reqparse.RequestParser()
project_filter_parser.add_argument("offset", type=int, default=0, help="Offset for pagination")
project_filter_parser.add_argument("limit", type=int, default=10, help="Limit for pagination")
project_filter_parser.add_argument("sort_by", type=str, required=False, help="Поле для сортировки")
project_filter_parser.add_argument("sort_order", type=str, required=False, choices=["asc", "desc"], help="Порядок сортировки")
project_filter_parser.add_argument("object", type=str, required=False, help="Filter by object ID")
project_filter_parser.add_argument("project_leader", type=str, required=False, help="Filter by project leader ID")
project_filter_parser.add_argument("created_by", type=str, required=False, help="Filter by creator ID")
project_filter_parser.add_argument("name", type=str, help="Filter by name")
project_filter_parser.add_argument("created_at", type=int, required=False, help="Filter by Unix epoch milliseconds")
project_filter_parser.add_argument(
    "night_shift_available",
    type=lambda x: x.lower() in ["true", "1"],
    required=False,
    help="Flag filter",
)
project_filter_parser.add_argument(
    "extreme_conditions_available",
    type=lambda x: x.lower() in ["true", "1"],
    required=False,
    help="Flag filter",
)
project_filter_parser.add_argument(
    "deleted",
    type=lambda x: x.lower() in ["true", "1"],
    required=False,
    help="Flag filter",
)
