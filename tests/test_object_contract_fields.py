from datetime import date
from typing import cast
from uuid import uuid4

from app.adapters.objects import object_dict_to_entity, object_entity_to_response
from app.schemas.object_schemas import ObjectCreateSchema, ObjectEditSchema


def test_object_create_and_edit_schemas_accept_contract_fields():
    create_schema = ObjectCreateSchema()
    edit_data = cast(
        dict[str, object],
        ObjectEditSchema().load(
            {
                "contract_start_date": "2026-02-01",
                "contract_end_date": None,
                "order_number": "ORDER-43",
                "monthly_ks_closing_date": 20,
            }
        ),
    )

    assert set(
        ("contract_start_date", "contract_end_date", "order_number", "monthly_ks_closing_date")
    ).issubset(create_schema.fields)
    assert edit_data["contract_start_date"] == date(2026, 2, 1)
    assert edit_data["contract_end_date"] is None


def test_object_mapper_preserves_contract_fields_in_response():
    obj = object_dict_to_entity(
        {
            "object_id": str(uuid4()),
            "name": "Object",
            "address": None,
            "description": None,
            "city": None,
            "status": "active",
            "manager": None,
            "lng": None,
            "ltd": None,
            "contract_start_date": date(2026, 1, 15),
            "contract_end_date": date(2026, 12, 31),
            "order_number": "ORDER-42",
            "monthly_ks_closing_date": 25,
            "created_by": None,
            "created_at": 1,
            "deleted": False,
        }
    )

    response = object_entity_to_response(obj)

    assert response["contract_start_date"] == date(2026, 1, 15)
    assert response["contract_end_date"] == date(2026, 12, 31)
    assert response["order_number"] == "ORDER-42"
    assert response["monthly_ks_closing_date"] == 25
