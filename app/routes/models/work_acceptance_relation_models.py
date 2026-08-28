from flask_restx import Model, fields, reqparse
from app.routes.models._crud_helpers import crud_models
from app.schemas.work_acceptance_relation_schemas import WorkAcceptanceRelationCreateSchema, WorkAcceptanceRelationEditSchema

work_acceptance_relation_create_model = crud_models(WorkAcceptanceRelationCreateSchema(), "WorkAcceptanceRelationCreate")
work_acceptance_relation_edit_model = crud_models(WorkAcceptanceRelationEditSchema(), "WorkAcceptanceRelationEdit")
work_acceptance_relation_model = Model("WorkAcceptanceRelation", {
    "id": fields.String(required=True), "acceptance_id": fields.String(required=True),
    "work_id": fields.String(required=True), "quantity": fields.Float(required=True),
})
work_acceptance_relation_msg_model = Model("WorkAcceptanceRelationMessage", {"msg": fields.String(required=True), "id": fields.String()})
work_acceptance_relation_response = Model("WorkAcceptanceRelationResponse", {"msg": fields.String(required=True), "work_acceptance_relation": fields.Nested(work_acceptance_relation_model, required=True)})
work_acceptance_relation_all_response = Model("WorkAcceptanceRelationAllResponse", {"msg": fields.String(required=True), "work_acceptance_relations": fields.List(fields.Nested(work_acceptance_relation_model))})
work_acceptance_relation_filter_parser = reqparse.RequestParser()
work_acceptance_relation_filter_parser.add_argument("offset", type=int, default=0)
work_acceptance_relation_filter_parser.add_argument("limit", type=int, default=1000)
work_acceptance_relation_filter_parser.add_argument("acceptance_id", type=str)
work_acceptance_relation_filter_parser.add_argument("work_id", type=str)
