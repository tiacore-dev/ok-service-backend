from flask_restx import Model, fields, reqparse
from app.schemas.object_schemas import ObjectCreateSchema
from app.utils.helpers import generate_swagger_model


object_create_model = generate_swagger_model(
    ObjectCreateSchema(), "ObjectCreate")


object_model = Model('Object', {
    "object_id": fields.String(required=True, description="ID of the object"),
    "name": fields.String(required=True, description="Name of the object"),
    "address": fields.String(required=False, description="Address of the object"),
    "description": fields.String(required=False, description="Description of the object"),
    "status": fields.String(required=False, description="Status of the object"),
    "deleted": fields.Boolean(required=True, description="Deletion status")
})


object_msg_model = Model('ObjectMessage', {
    "msg": fields.String(required=True, description="Response message"),
    "object_id": fields.String(description="ID of object")
})

object_response = Model('ObjectResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "object": fields.Nested(object_model, required=True)
})

object_all_response = Model('ObjectAllResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "objects": fields.List(fields.Nested(object_model), description="List of objects")
})

object_filter_parser = reqparse.RequestParser()
object_filter_parser.add_argument(
    'offset', type=int, default=0, help="Offset for pagination")
object_filter_parser.add_argument(
    'limit', type=int, default=10, help="Limit for pagination")
object_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Поле для сортировки')
object_filter_parser.add_argument('sort_order', type=str, required=False, choices=[
    'asc', 'desc'], help='Порядок сортировки')
object_filter_parser.add_argument('name', type=str, help="Filter by name")
object_filter_parser.add_argument(
    'deleted',
    # Интерпретация значения как логического
    type=lambda x: x.lower() in ['true', '1'],
    required=False,
    help="Флаг для фильтрации по удаленным отчетам"
)
object_filter_parser.add_argument(
    'address', type=str, required=False, help="Filter by address"
)
object_filter_parser.add_argument(
    'status', type=str, required=False, help="Filter by object status"
)
