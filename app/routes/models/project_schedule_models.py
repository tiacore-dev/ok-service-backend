# Models for project schedules namespace
from flask_restx import Model, fields, reqparse
from app.schemas.project_schedule_schemas import ProjectScheduleCreateSchema
from app.utils.helpers import generate_swagger_model

# Модель для создания проекта
project_schedule_create_model = generate_swagger_model(
    ProjectScheduleCreateSchema(), "ProjectScheduleCreate")


project_schedule_model = Model('ProjectSchedule', {
    "project_schedule_id": fields.String(required=True, description="ID of the project schedule"),
    "work": fields.String(required=True, description="Work details"),
    "quantity": fields.Float(required=True, description="Quantity of work"),
    "date": fields.Integer(required=False, description="Scheduled date")
})

project_schedule_msg_model = Model('ProjectScheduleMessage', {
    "msg": fields.String(required=True, description="Response message"),
    "project_schedule_id": fields.String(description="ID of project schedule")
})

project_schedule_response = Model('ProjectScheduleResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "project_schedule": fields.Nested(project_schedule_model, required=True)
})

project_schedule_all_response = Model('ProjectScheduleAllResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "project_schedules": fields.List(fields.Nested(project_schedule_model), description="List of project schedules")
})

project_schedule_filter_parser = reqparse.RequestParser()
project_schedule_filter_parser.add_argument(
    'offset', type=int, default=0, help="Offset for pagination")
project_schedule_filter_parser.add_argument(
    'limit', type=int, default=10, help="Limit for pagination")
project_schedule_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Field for sorting')
project_schedule_filter_parser.add_argument('sort_order', type=str, required=False, choices=[
    'asc', 'desc'], help='Sort order')
project_schedule_filter_parser.add_argument(
    'work', type=str, help="Filter by work ID")
project_schedule_filter_parser.add_argument(
    'date', type=int, help="Filter by date")
