from flask_restx import Model, fields, reqparse

from app.schemas.leave_schemas import LeaveCreateSchema, LeaveEditSchema
from app.utils.helpers import generate_swagger_model

leave_create_model = generate_swagger_model(LeaveCreateSchema(), "LeaveCreate")
leave_edit_model = generate_swagger_model(LeaveEditSchema(), "LeaveEdit")

leave_model = Model(
    "Leave",
    {
        "leave_id": fields.String(required=True, description="ID листа отсутствия"),
        "start_date": fields.Integer(required=True, description="Дата начала"),
        "end_date": fields.Integer(required=True, description="Дата окончания"),
        "reason": fields.String(required=True, description="Причина отсутствия"),
        "user": fields.String(required=True, description="Сотрудник"),
        "responsible": fields.String(required=True, description="Ответственный"),
        "comment": fields.String(required=False, description="Комментарий"),
        "created_by": fields.String(required=True, description="Кем создан"),
        "created_at": fields.Integer(required=True, description="Когда создан"),
        "updated_by": fields.String(required=False, description="Кем изменен"),
        "updated_at": fields.Integer(required=False, description="Когда изменен"),
        "deleted": fields.Boolean(required=True, description="Удален ли лист"),
    },
)

leave_msg_model = Model(
    "LeaveMessage",
    {
        "msg": fields.String(required=True, description="Сообщение"),
        "leave_id": fields.String(description="ID листа отсутствия"),
    },
)

leave_response = Model(
    "LeaveResponse",
    {
        "msg": fields.String(required=True, description="Сообщение"),
        "leave": fields.Nested(
            leave_model, required=True, description="Лист отсутствия"
        ),
    },
)

leave_all_response = Model(
    "LeaveAllResponse",
    {
        "msg": fields.String(required=True, description="Сообщение"),
        "leaves": fields.List(
            fields.Nested(leave_model), description="Список листов отсутствия"
        ),
    },
)

leave_filter_parser = reqparse.RequestParser()
leave_filter_parser.add_argument(
    "offset", type=int, default=0, required=False, help="Смещение"
)
leave_filter_parser.add_argument(
    "limit", type=int, default=10, required=False, help="Лимит"
)
leave_filter_parser.add_argument(
    "sort_by", type=str, required=False, help="Поле сортировки"
)
leave_filter_parser.add_argument(
    "sort_order",
    type=str,
    required=False,
    choices=["asc", "desc"],
    help="Направление сортировки",
)
leave_filter_parser.add_argument(
    "user", type=str, required=False, help="Фильтр по сотруднику"
)
leave_filter_parser.add_argument(
    "responsible", type=str, required=False, help="Фильтр по ответственному"
)
leave_filter_parser.add_argument(
    "reason", type=str, required=False, help="Фильтр по причине"
)
leave_filter_parser.add_argument(
    "date_from", type=int, required=False, help="Дата начала периода"
)
leave_filter_parser.add_argument(
    "date_to", type=int, required=False, help="Дата конца периода"
)
leave_filter_parser.add_argument(
    "deleted",
    type=lambda x: x.lower() in ["true", "1"],
    required=False,
    help="Фильтр по удаленным листам",
)
