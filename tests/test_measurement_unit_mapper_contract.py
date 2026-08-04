from uuid import uuid4

from app.adapters.materials.mappers import material_entity_to_create_payload
from app.adapters.works.mappers import work_entity_to_create_payload
from app.domain.materials import Material
from app.domain.works import Work


def test_material_update_payload_extracts_nested_measurement_unit_id():
    unit_id = uuid4()
    material = Material(
        material_id=uuid4(),
        name="Sand",
        measurement_unit={"measurement_unit_id": str(unit_id), "name": "м"},
        created_by=uuid4(),
        created_at=1,
    )

    assert material_entity_to_create_payload(material)["measurement_unit"] == unit_id


def test_work_update_payload_extracts_nested_measurement_unit_id():
    unit_id = uuid4()
    work = Work(
        work_id=uuid4(),
        name="Installation",
        category=None,
        measurement_unit={"measurement_unit_id": str(unit_id), "name": "м"},
        created_at=1,
        created_by=uuid4(),
        deleted=False,
    )

    assert work_entity_to_create_payload(work)["measurement_unit"] == unit_id
