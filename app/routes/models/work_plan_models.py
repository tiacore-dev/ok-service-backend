from flask_restx import Model, fields, reqparse

from app.schemas.work_plan_schemas import WorkPlanCreateSchema, WorkPlanEditSchema
from app.utils.helpers import generate_swagger_model

work_plan_create_model = generate_swagger_model(WorkPlanCreateSchema(), "WorkPlanCreate")
work_plan_edit_model = generate_swagger_model(WorkPlanEditSchema(), "WorkPlanEdit")
work_plan_model = Model(
    "WorkPlan",
    {
        "work_plan_id": fields.String(required=True),
        "user_id": fields.String(required=False, allow_null=True),
        "date": fields.String(required=True, description="First day of the month"),
        "summ": fields.String(required=True, description="Decimal amount with up to two fractional digits"),
        "description": fields.String(required=False, allow_null=True),
        "deleted": fields.Boolean(required=True),
    },
)
work_plan_msg_model = Model(
    "WorkPlanMessage", {"msg": fields.String(required=True), "work_plan_id": fields.String()}
)
work_plan_response = Model(
    "WorkPlanResponse", {"msg": fields.String(required=True), "work_plan": fields.Nested(work_plan_model, required=True)}
)
work_plan_all_response = Model(
    "WorkPlanAllResponse", {"msg": fields.String(required=True), "work_plans": fields.List(fields.Nested(work_plan_model))}
)
work_plan_filter_parser = reqparse.RequestParser()
for name, arg_type in (("offset", int), ("limit", int), ("year", int)):
    work_plan_filter_parser.add_argument(name, type=arg_type, required=False)
work_plan_filter_parser.add_argument("sort_by", type=str, required=False)
work_plan_filter_parser.add_argument("sort_order", type=str, choices=["asc", "desc"], required=False)
work_plan_filter_parser.add_argument("user_id", type=str, required=False)
work_plan_filter_parser.add_argument("user_id_is_null", type=lambda x: x.lower() in ["true", "1"], required=False)
work_plan_filter_parser.add_argument("deleted", type=lambda x: x.lower() in ["true", "1"], required=False)
