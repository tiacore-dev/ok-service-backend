from marshmallow import Schema, fields, validate


def _place_ids():
    return fields.List(fields.UUID(), required=True, validate=validate.Length(min=1))


class ProjectPlaceRelationCreateSchema(Schema):
    project_id = fields.UUID(required=True)
    place_id = fields.UUID(required=True)


class ProjectPlaceRelationEditSchema(Schema):
    project_id = fields.UUID(required=True)
    place_id = fields.UUID(required=True)


class ProjectPlaceRelationBulkSchema(Schema):
    project_id = fields.UUID(required=True)
    place_ids = _place_ids()


class ShiftPlaceRelationCreateSchema(Schema):
    shift_report_id = fields.UUID(required=True)
    place_id = fields.UUID(required=True)
    comment = fields.String(required=False, allow_none=True)


class ShiftPlaceRelationEditSchema(Schema):
    place_id = fields.UUID(required=False)
    comment = fields.String(required=False, allow_none=True)


class ShiftPlaceRelationBulkSchema(Schema):
    shift_report_id = fields.UUID(required=True)
    place_ids = _place_ids()
