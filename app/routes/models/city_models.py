from flask_restx import Model, fields, reqparse

from app.schemas.city_schemas import CityCreateSchema
from app.utils.helpers import generate_swagger_model

city_create_model = generate_swagger_model(CityCreateSchema(), "CityCreate")

city_model = Model(
    "City",
    {
        "city_id": fields.String(required=True, description="ID города"),
        "name": fields.String(required=True, description="Название города"),
        "created_by": fields.String(required=True, description="Автор создания"),
        "created_at": fields.Integer(required=True, description="Дата создания"),
        "deleted": fields.Boolean(required=True, description="Признак удаления"),
    },
)

city_msg_model = Model(
    "CityMessage",
    {
        "msg": fields.String(required=True, description="Сообщение"),
        "city_id": fields.String(description="ID города"),
    },
)

city_response = Model(
    "CityResponse",
    {
        "msg": fields.String(required=True, description="Сообщение"),
        "city": fields.Nested(city_model, required=True, description="Данные города"),
    },
)

city_all_response = Model(
    "CityAllResponse",
    {
        "msg": fields.String(required=True, description="Сообщение"),
        "cities": fields.List(
            fields.Nested(city_model), description="Список доступных городов"
        ),
    },
)

city_filter_parser = reqparse.RequestParser()
city_filter_parser.add_argument(
    "offset", type=int, required=False, default=0, help="Смещение для пагинации"
)
city_filter_parser.add_argument(
    "limit", type=int, required=False, default=10, help="Лимит записей"
)
city_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Поле для сортировки"
)
city_filter_parser.add_argument(
    "sort_order",
    type=str,
    required=False,
    choices=["asc", "desc"],
    help="Порядок сортировки",
)
city_filter_parser.add_argument(
    "name", type=str, required=False, help="Фильтр по названию города"
)
city_filter_parser.add_argument(
    "deleted",
    type=lambda x: x.lower() in ["true", "1"],
    required=False,
    help="Фильтр по удаленным записям",
)
