from flask_restx import Model, fields, reqparse
from app.schemas.measurement_unit_schemas import MeasurementUnitCreateSchema, MeasurementUnitEditSchema
from app.utils.helpers import generate_swagger_model

measurement_unit_create_model = generate_swagger_model(MeasurementUnitCreateSchema(), "MeasurementUnitCreate")
measurement_unit_edit_model = generate_swagger_model(MeasurementUnitEditSchema(), "MeasurementUnitEdit")
measurement_unit_model = Model("MeasurementUnit", {
    "measurement_unit_id": fields.String(required=True),
    "name": fields.String(required=True),
    "created_at": fields.Integer(required=True),
    "created_by": fields.String(required=False, allow_none=True),
})
measurement_unit_msg_model = Model("MeasurementUnitMessage", {
    "msg": fields.String(required=True), "measurement_unit_id": fields.String()
})
measurement_unit_response = Model("MeasurementUnitResponse", {
    "msg": fields.String(required=True), "measurement_unit": fields.Nested(measurement_unit_model, required=True)
})
measurement_unit_all_response = Model("MeasurementUnitAllResponse", {
    "msg": fields.String(required=True), "measurement_units": fields.List(fields.Nested(measurement_unit_model))
})
measurement_unit_filter_parser = reqparse.RequestParser()
measurement_unit_filter_parser.add_argument("offset", type=int, default=0)
measurement_unit_filter_parser.add_argument("limit", type=int, default=1000)
measurement_unit_filter_parser.add_argument("name", type=str)
