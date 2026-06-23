from marshmallow import Schema, fields, validate


class RoleFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Исключать лишние поля

    offset = fields.Int(
        required=False,
        load_default=0,
        validate=validate.Range(min=0, error="Offset must be non-negative."),
        metadata={"description": "Смещение для пагинации."},
    )
    limit = fields.Int(
        required=False,
        load_default=1000,
        validate=validate.Range(min=1, error="Limit must be at least 1."),
        metadata={"description": "Лимит записей."},
    )
    sort_by = fields.String(
        required=False,
        metadata={"description": "Поле для сортировки."},
    )
    sort_order = fields.String(
        required=False,
        validate=validate.OneOf(
            ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."),
        metadata={"description": "Порядок сортировки."},
    )
    role_id = fields.String(
        required=False,
        metadata={"description": "Фильтр по идентификатору роли."},
    )
    name = fields.String(
        required=False,
        metadata={"description": "Фильтр по названию роли."},
    )
