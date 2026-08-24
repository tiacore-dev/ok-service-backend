from uuid import uuid4

import pytest
from marshmallow import ValidationError

from app.schemas.place_schemas import PlaceCreateSchema, PlaceEditSchema


def test_place_create_schema_requires_object_and_name():
    payload = PlaceCreateSchema().load(
        {"object_id": str(uuid4()), "name": "Main hall", "description": None}
    )
    assert isinstance(payload, dict)
    assert payload["name"] == "Main hall"
    assert payload["description"] is None

    with pytest.raises(ValidationError):
        PlaceCreateSchema().load({"object_id": str(uuid4())})


def test_place_edit_schema_is_partial_and_accepts_deleted_flag():
    payload = PlaceEditSchema().load({"deleted": True})
    assert payload == {"deleted": True}
