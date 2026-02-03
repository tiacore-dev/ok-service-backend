from flask_restx import Model, fields, reqparse

from app.schemas.material_schemas import MaterialCreateSchema
from app.utils.helpers import generate_swagger_model

material_create_model = generate_swagger_model(
    MaterialCreateSchema(), "MaterialCreate"
)

material_model = Model(
    "Material",
    {
        "material_id": fields.String(required=True, description="ID of the material"),
        "name": fields.String(required=True, description="Name of the material"),
        "measurement_unit": fields.String(
            required=False, description="Measurement unit of the material"
        ),
        "created_at": fields.Integer(required=True, description="Created at timestamp"),
        "created_by": fields.String(required=True, description="Creator of material"),
        "deleted": fields.Boolean(required=True, description="Deletion status"),
    },
)

material_msg_model = Model(
    "MaterialMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
        "material_id": fields.String(description="ID of material"),
    },
)

material_response = Model(
    "MaterialResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "material": fields.Nested(material_model, required=True),
    },
)

material_all_response = Model(
    "MaterialAllResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "materials": fields.List(
            fields.Nested(material_model), description="List of materials"
        ),
    },
)

material_filter_parser = reqparse.RequestParser()
material_filter_parser.add_argument(
    "offset", type=int, default=0, help="Offset for pagination"
)
material_filter_parser.add_argument(
    "limit", type=int, default=10, help="Limit for pagination"
)
material_filter_parser.add_argument("name", type=str, help="Filter by name")
material_filter_parser.add_argument(
    "measurement_unit", type=str, help="Filter by measurement unit"
)
material_filter_parser.add_argument(
    "deleted",
    type=lambda x: x.lower() in ["true", "1"],
    help="Filter by deletion status",
)
material_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Field for sorting"
)
material_filter_parser.add_argument(
    "sort_order", type=str, required=False, choices=["asc", "desc"], help="Sort order"
)
