from flask_restx import Model, fields, reqparse

from app.schemas.work_material_relation_schemas import (
    WorkMaterialRelationCreateSchema,
)
from app.utils.helpers import generate_swagger_model

work_material_relation_create_model = generate_swagger_model(
    WorkMaterialRelationCreateSchema(), "WorkMaterialRelationCreate"
)

work_material_relation_model = Model(
    "WorkMaterialRelation",
    {
        "work_material_relation_id": fields.String(
            required=True, description="ID of the work material relation"
        ),
        "work": fields.String(required=True, description="Work ID"),
        "material": fields.String(required=True, description="Material ID"),
        "quantity": fields.Float(required=True, description="Quantity of material"),
        "created_at": fields.Integer(required=True, description="Created at timestamp"),
        "created_by": fields.String(required=True, description="Creator of relation"),
    },
)

work_material_relation_msg_model = Model(
    "WorkMaterialRelationMessage",
    {
        "msg": fields.String(required=True, description="Response message"),
        "work_material_relation_id": fields.String(
            description="ID of work material relation"
        ),
    },
)

work_material_relation_response = Model(
    "WorkMaterialRelationResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "work_material_relation": fields.Nested(
            work_material_relation_model, required=True
        ),
    },
)

work_material_relation_all_response = Model(
    "WorkMaterialRelationAllResponse",
    {
        "msg": fields.String(required=True, description="Response message"),
        "work_material_relations": fields.List(
            fields.Nested(work_material_relation_model),
            description="List of work material relations",
        ),
    },
)

work_material_relation_filter_parser = reqparse.RequestParser()
work_material_relation_filter_parser.add_argument(
    "offset", type=int, default=0, help="Offset for pagination"
)
work_material_relation_filter_parser.add_argument(
    "limit", type=int, default=10, help="Limit for pagination"
)
work_material_relation_filter_parser.add_argument(
    "work", type=str, required=False, help="Filter by work ID"
)
work_material_relation_filter_parser.add_argument(
    "material", type=str, required=False, help="Filter by material ID"
)
work_material_relation_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Field for sorting"
)
work_material_relation_filter_parser.add_argument(
    "sort_order", type=str, required=False, choices=["asc", "desc"], help="Sort order"
)
