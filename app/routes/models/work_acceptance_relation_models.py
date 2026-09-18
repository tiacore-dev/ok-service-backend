from flask_restx import Model, fields, reqparse
from app.routes.models._crud_helpers import crud_models
from app.schemas.work_acceptance_relation_schemas import (
    WorkAcceptanceRelationBulkCreateSchema,
    WorkAcceptanceRelationBulkDeleteSchema,
    WorkAcceptanceRelationBulkWorkSchema,
    WorkAcceptanceRelationCreateSchema,
    WorkAcceptanceRelationEditSchema,
)
from app.utils.helpers import generate_swagger_model

work_acceptance_relation_create_model = crud_models(WorkAcceptanceRelationCreateSchema(), "WorkAcceptanceRelationCreate")
work_acceptance_relation_edit_model = crud_models(WorkAcceptanceRelationEditSchema(), "WorkAcceptanceRelationEdit")
work_acceptance_relation_bulk_work_model = generate_swagger_model(WorkAcceptanceRelationBulkWorkSchema(), "WorkAcceptanceRelationBulkWork")
work_acceptance_relation_bulk_create_model = generate_swagger_model(WorkAcceptanceRelationBulkCreateSchema(), "WorkAcceptanceRelationBulkCreate")
work_acceptance_relation_bulk_delete_model = generate_swagger_model(WorkAcceptanceRelationBulkDeleteSchema(), "WorkAcceptanceRelationBulkDelete")
work_acceptance_relation_model = Model("WorkAcceptanceRelation", {
    "id": fields.String(required=True), "acceptance_id": fields.String(required=True),
    "work_id": fields.String(required=True), "quantity": fields.Float(required=True),
})
work_acceptance_relation_msg_model = Model("WorkAcceptanceRelationMessage", {
    "msg": fields.String(required=True), "id": fields.String(), "code": fields.String(),
    "work_id": fields.String(), "specification_quantity": fields.Float(),
    "available_quantity": fields.Float(), "requested_quantity": fields.Float(),
    "exceeded_quantity": fields.Float(),
})
work_acceptance_relation_response = Model("WorkAcceptanceRelationResponse", {"msg": fields.String(required=True), "work_acceptance_relation": fields.Nested(work_acceptance_relation_model, required=True)})
work_acceptance_relation_all_response = Model("WorkAcceptanceRelationAllResponse", {"msg": fields.String(required=True), "work_acceptance_relations": fields.List(fields.Nested(work_acceptance_relation_model))})
work_acceptance_relation_bulk_create_response = Model("WorkAcceptanceRelationBulkCreateResponse", {"msg": fields.String(required=True), "ids": fields.List(fields.String, required=True), "created_count": fields.Integer(required=True)})
work_acceptance_relation_bulk_delete_response = Model("WorkAcceptanceRelationBulkDeleteResponse", {"msg": fields.String(required=True), "deleted_count": fields.Integer(required=True)})
work_acceptance_relation_filter_parser = reqparse.RequestParser()
work_acceptance_relation_filter_parser.add_argument("offset", type=int, default=0)
work_acceptance_relation_filter_parser.add_argument("limit", type=int, default=1000)
work_acceptance_relation_filter_parser.add_argument("acceptance_id", type=str)
work_acceptance_relation_filter_parser.add_argument("work_id", type=str)
