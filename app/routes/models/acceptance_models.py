from flask_restx import Model, fields, reqparse
from app.routes.models._crud_helpers import crud_models
from app.schemas.acceptance_schemas import AcceptanceCreateSchema, AcceptanceEditSchema, ACCEPTANCE_STATUSES

acceptance_create_model = crud_models(AcceptanceCreateSchema(), "AcceptanceCreate")
acceptance_edit_model = crud_models(AcceptanceEditSchema(), "AcceptanceEdit")
acceptance_model = Model("Acceptance", {
    "id": fields.String(required=True), "date": fields.Integer(required=True),
    "project_id": fields.String(required=True), "status": fields.String(required=True, enum=ACCEPTANCE_STATUSES),
    "comment": fields.String(required=False, allow_null=True),
})
acceptance_msg_model = Model("AcceptanceMessage", {"msg": fields.String(required=True), "id": fields.String()})
acceptance_response = Model("AcceptanceResponse", {"msg": fields.String(required=True), "acceptance": fields.Nested(acceptance_model, required=True)})
acceptance_all_response = Model("AcceptanceAllResponse", {"msg": fields.String(required=True), "acceptances": fields.List(fields.Nested(acceptance_model))})
acceptance_filter_parser = reqparse.RequestParser()
acceptance_filter_parser.add_argument("offset", type=int, default=0)
acceptance_filter_parser.add_argument("limit", type=int, default=1000)
acceptance_filter_parser.add_argument("project_id", type=str)
acceptance_filter_parser.add_argument("status", type=str, choices=ACCEPTANCE_STATUSES)

acceptance_history_model = Model("AcceptanceStatusHistory", {
    "id": fields.String(required=True),
    "acceptance_id": fields.String(required=True),
    "changed_at": fields.Integer(required=True),
    "changed_by": fields.String(required=True),
    "from_status": fields.String(required=True, enum=ACCEPTANCE_STATUSES),
    "to_status": fields.String(required=True, enum=ACCEPTANCE_STATUSES),
})
acceptance_history_response = Model("AcceptanceHistoryResponse", {
    "msg": fields.String(required=True),
    "history": fields.List(fields.Nested(acceptance_history_model), required=True),
})
acceptance_history_filter_parser = reqparse.RequestParser()
acceptance_history_filter_parser.add_argument("offset", type=int, default=0)
acceptance_history_filter_parser.add_argument("limit", type=int, default=1000)
