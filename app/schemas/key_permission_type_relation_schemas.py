from marshmallow import Schema, fields, validate


class KeyPermissionTypeRelationCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    api_key_id = fields.String(
        required=True, error_messages={"required": "Field 'api_key_id' is required."}
    )
    permission_type_id = fields.String(
        required=True,
        error_messages={"required": "Field 'permission_type_id' is required."},
    )


class KeyPermissionTypeRelationBulkCreateSchema(Schema):
    class Meta:
        unknown = "exclude"

    api_key_id = fields.String(
        required=True, error_messages={"required": "Field 'api_key_id' is required."}
    )
    permission_type_ids = fields.List(
        fields.String(required=True),
        required=True,
        validate=validate.Length(min=1),
        error_messages={"required": "Field 'permission_type_ids' is required."},
    )


class KeyPermissionTypeRelationBulkDeleteSchema(Schema):
    class Meta:
        unknown = "exclude"

    relation_ids = fields.List(
        fields.String(required=True),
        required=True,
        validate=validate.Length(min=1),
        error_messages={"required": "Field 'relation_ids' is required."},
    )


class PermissionTypeFilterSchema(Schema):
    class Meta:
        unknown = "exclude"

    offset = fields.Int(
        required=False,
        load_default=0,
        validate=validate.Range(min=0, error="Offset must be non-negative."),
    )
    limit = fields.Int(
        required=False,
        load_default=1000,
        validate=validate.Range(min=1, error="Limit must be at least 1."),
    )
    sort_by = fields.String(required=False)
    sort_order = fields.String(
        required=False,
        validate=validate.OneOf(
            ["asc", "desc"], error="Sort order must be 'asc' or 'desc'."
        ),
    )
