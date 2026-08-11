from flask_restx import Model, fields
from app.schemas.place_relation_schemas import (
    ProjectPlaceRelationCreateSchema, ProjectPlaceRelationEditSchema,
    ShiftPlaceRelationCreateSchema, ShiftPlaceRelationEditSchema,
)
from app.utils.helpers import generate_swagger_model

project_place_relation_create_model = generate_swagger_model(ProjectPlaceRelationCreateSchema(), "ProjectPlaceRelationCreate")
project_place_relation_edit_model = generate_swagger_model(ProjectPlaceRelationEditSchema(), "ProjectPlaceRelationEdit")
shift_place_relation_create_model = generate_swagger_model(ShiftPlaceRelationCreateSchema(), "ShiftPlaceRelationCreate")
shift_place_relation_edit_model = generate_swagger_model(ShiftPlaceRelationEditSchema(), "ShiftPlaceRelationEdit")

project_place_relation_model = Model("ProjectPlaceRelation", {
    "project_place_relation_id": fields.String(required=True), "project_id": fields.String(required=True), "place_id": fields.String(required=True),
})
shift_place_relation_model = Model("ShiftPlaceRelation", {
    "shift_place_relation_id": fields.String(required=True), "shift_report_id": fields.String(required=True), "place_id": fields.String(required=True), "comment": fields.String(allow_none=True),
})
project_place_relation_msg_model = Model("ProjectPlaceRelationMessage", {"msg": fields.String(required=True), "project_place_relation_id": fields.String()})
shift_place_relation_msg_model = Model("ShiftPlaceRelationMessage", {"msg": fields.String(required=True), "shift_place_relation_id": fields.String()})
project_place_relation_response = Model("ProjectPlaceRelationResponse", {"msg": fields.String(required=True), "project_place_relation": fields.Nested(project_place_relation_model, required=True)})
shift_place_relation_response = Model("ShiftPlaceRelationResponse", {"msg": fields.String(required=True), "shift_place_relation": fields.Nested(shift_place_relation_model, required=True)})
project_place_relation_all_response = Model("ProjectPlaceRelationAllResponse", {"msg": fields.String(required=True), "project_place_relations": fields.List(fields.Nested(project_place_relation_model))})
shift_place_relation_all_response = Model("ShiftPlaceRelationAllResponse", {"msg": fields.String(required=True), "shift_place_relations": fields.List(fields.Nested(shift_place_relation_model))})
