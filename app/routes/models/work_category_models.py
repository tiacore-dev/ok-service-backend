from flask_restx import Model, fields
from flask_restx import reqparse

work_category_create_model = Model('WorkCategoryCreate', {
    'name': fields.String(required=True, description='Name of the work category.')
})

work_category_model = Model('WorkCategory', {
    "work_category_id": fields.String(required=True, description='ID of the work category'),
    "name": fields.String(required=True, description='Name of the work category'),
    "deleted": fields.Boolean(required=True, description='Deleted status of the work category')
})

work_category_response = Model('WorkCategoryresponse', {
    'msg': fields.String(description='Response message'),
    'work_category': fields.Nested(work_category_model, required=True, description='Данные о категории.')
})

work_category_all_response = Model('WorkCategoryAllResponse', {
    'msg': fields.String(description='Response message'),
    'work_categories': fields.List(fields.Nested(work_category_model), description='List of work categories')
})

work_category_msg_model = Model('WorkCategoryMessage', {
    'msg': fields.String(description='Response message')
})


work_category_filter_parser = reqparse.RequestParser()
work_category_filter_parser.add_argument(
    'offset', type=int, required=False, default=0, help='Offset for pagination')
work_category_filter_parser.add_argument(
    'limit', type=int, required=False, default=10, help='Limit for pagination')
work_category_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Field for sorting')
work_category_filter_parser.add_argument(
    'sort_order', type=str, required=False, choices=['asc', 'desc'], help='Sorting order')
work_category_filter_parser.add_argument(
    'name', type=str, required=False, help='Filter by name')
work_category_filter_parser.add_argument(
    'deleted', type=bool, required=False, help='Filter by deleted status')
