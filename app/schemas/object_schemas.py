from marshmallow import Schema, fields
from app.schemas.validators import validate_object_status_exists, validate_user_exists


class ObjectCreateSchema(Schema):
    class Meta:
        unknown = "exclude"  # Игнорировать лишние поля
    name = fields.String(required=True, error_messages={
                         "required": "Field 'name' is required."})
    address = fields.String(required=False)
    description = fields.String(required=False)
    manager = fields.String(required=True, validate=[
        validate_user_exists], error_messages={
        "required": "Field 'name' is required."})
    status = fields.String(required=False, validate=[
                           validate_object_status_exists])


class ObjectEditSchema(Schema):
    class Meta:
        unknown = "exclude"  # Игнорировать лишние поля
    name = fields.String(required=False, allow_none=True)
    address = fields.String(required=False, allow_none=True)
    description = fields.String(required=False, allow_none=True)
    status = fields.String(required=False, allow_none=True, validate=[
                           validate_object_status_exists])
    manager = fields.String(required=False, validate=[
        validate_user_exists], allow_none=True)
    deleted = fields.Boolean(required=False, allow_none=True)


class ObjectFilterSchema(Schema):
    class Meta:
        unknown = "exclude"  # Игнорировать лишние поля
    offset = fields.Int(required=False, missing=0)
    limit = fields.Int(required=False, missing=10)
    sort_by = fields.String(required=False)
    sort_order = fields.String(
        required=False, validate=lambda x: x in ["asc", "desc"])
    address = fields.String(required=False)
    status = fields.String(required=False)
    name = fields.String(required=False)
    manager = fields.String(required=False)
    deleted = fields.Boolean(required=False)
