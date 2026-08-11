from marshmallow import Schema, fields


class ProjectPlaceRelationCreateSchema(Schema):
    project_id = fields.UUID(required=True)
    place_id = fields.UUID(required=True)


class ProjectPlaceRelationEditSchema(Schema):
    project_id = fields.UUID(required=True)
    place_id = fields.UUID(required=True)


class ShiftPlaceRelationCreateSchema(Schema):
    shift_report_id = fields.UUID(required=True)
    place_id = fields.UUID(required=True)
    comment = fields.String(required=False, allow_none=True)


class ShiftPlaceRelationEditSchema(Schema):
    place_id = fields.UUID(required=False)
    comment = fields.String(required=False, allow_none=True)
