from flask_restx import Model, fields, reqparse

from app.schemas.project_material_schemas import ProjectMaterialCreateSchema
from app.utils.helpers import generate_swagger_model

project_material_create_model = generate_swagger_model(
    ProjectMaterialCreateSchema(), "ProjectMaterialCreate"
)

project_material_model = Model(
    "ProjectMaterial",
    {
        "project_material_id": fields.String(
            required=True, description="ID of the project material"
        ),
        "project": fields.String(required=True, description="Project ID"),
        "material": fields.String(required=True, description="Material ID"),
        "quantity": fields.Float(required=True, description="Quantity of material"),
        "project_work": fields.String(
            required=False, description="Project work ID (optional)"
        ),
        "created_at": fields.Integer(required=True, description="Created at timestamp"),
        "created_by": fields.String(required=True, description="Creator of record"),
    },
)

project_material_msg_model = Model(
    "ProjectMaterialMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
        "project_material_id": fields.String(description="ID of project material"),
    },
)

project_material_response = Model(
    "ProjectMaterialResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "project_material": fields.Nested(project_material_model, required=True),
    },
)

project_material_all_response = Model(
    "ProjectMaterialAllResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "project_materials": fields.List(
            fields.Nested(project_material_model),
            description="List of project materials",
        ),
    },
)

project_material_filter_parser = reqparse.RequestParser()
project_material_filter_parser.add_argument(
    "offset", type=int, default=0, help="Offset for pagination"
)
project_material_filter_parser.add_argument(
    "limit", type=int, default=10, help="Limit for pagination"
)
project_material_filter_parser.add_argument(
    "project", type=str, required=False, help="Filter by project ID"
)
project_material_filter_parser.add_argument(
    "material", type=str, required=False, help="Filter by material ID"
)
project_material_filter_parser.add_argument(
    "project_work", type=str, required=False, help="Filter by project work ID"
)
project_material_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Field for sorting"
)
project_material_filter_parser.add_argument(
    "sort_order", type=str, required=False, choices=["asc", "desc"], help="Sort order"
)
