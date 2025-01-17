from flask_restx import Model, fields, reqparse


# Модель для создания цены работы
work_price_create_model = Model('WorkPriceCreate', {
    "work": fields.String(required=True, description="ID of the associated work"),
    "name": fields.String(required=True, description="Name of the work price"),
    "category": fields.Integer(required=True, description="Category of the work price"),
    "price": fields.Float(required=True, description="Price of the work")
})

# Модель для объекта цены работы
work_price_model = Model('WorkPrice', {
    "work_price_id": fields.String(required=True, description="ID of the work price"),
    "work": fields.String(required=True, description="Associated work data"),
    "name": fields.String(required=True, description="Name of the work price"),
    "category": fields.Integer(required=True, description="Category of the work price"),
    "price": fields.Float(required=True, description="Price of the work"),
    "deleted": fields.Boolean(required=True, description="Deletion status")
})

# Модель для сообщений
work_price_msg_model = Model('WorkPriceMessage', {
    "msg": fields.String(required=True, description="Response message")
})

# Модель для ответа с одной ценой работы
work_price_response = Model('WorkPriceResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "work_price": fields.Nested(work_price_model, required=True)
})

# Модель для ответа со списком цен работы
work_price_all_response = Model('WorkPriceAllResponse', {
    "msg": fields.String(required=True, description="Response message"),
    "work_prices": fields.List(fields.Nested(work_price_model), description="List of work prices")
})

# Парсер для фильтрации, сортировки и пагинации
work_price_filter_parser = reqparse.RequestParser()
work_price_filter_parser.add_argument(
    'offset', type=int, default=0, help="Offset for pagination"
)
work_price_filter_parser.add_argument(
    'limit', type=int, default=10, help="Limit for pagination"
)
work_price_filter_parser.add_argument('name', type=str, help="Filter by name")
work_price_filter_parser.add_argument(
    'deleted',
    # Интерпретация значения как логического
    type=lambda x: x.lower() in ['true', '1'],
    required=False,
    help="Флаг для фильтрации по удаленным отчетам"
)
work_price_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Field for sorting'
)
work_price_filter_parser.add_argument(
    'sort_order', type=str, required=False, choices=['asc', 'desc'], help='Order of sorting'
)
