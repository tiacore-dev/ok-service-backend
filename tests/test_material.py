def test_add_material(client, jwt_token, db_session):
    from app.database.models import Materials

    data = {"name": "New Material", "measurement_unit": "pcs"}
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/materials/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New material added successfully"

    material = db_session.query(Materials).filter_by(name="New Material").first()
    assert material is not None
    assert str(material.material_id) == response.json["material_id"]
    assert material.name == "New Material"
    assert material.measurement_unit == "pcs"


def test_view_material(client, jwt_token, seed_material):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/materials/{str(seed_material['material_id'])}/view", headers=headers
    )

    assert response.status_code == 200
    assert "material" in response.json
    assert response.json["msg"] == "Material found successfully"

    material_data = response.json["material"]
    assert material_data["material_id"] == seed_material["material_id"]
    assert material_data["name"] == seed_material["name"]
    assert material_data["measurement_unit"] == seed_material["measurement_unit"]


def test_soft_delete_material(client, jwt_token, seed_material, db_session):
    from app.database.models import Materials

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/materials/{str(seed_material['material_id'])}/delete/soft", headers=headers
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Material {seed_material['material_id']} soft deleted successfully"
    )

    material = (
        db_session.query(Materials)
        .filter_by(material_id=seed_material["material_id"])
        .first()
    )
    assert material is not None
    assert material.deleted is True


def test_hard_delete_material(client, jwt_token, seed_material, db_session):
    from app.database.models import Materials

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/materials/{str(seed_material['material_id'])}/delete/hard", headers=headers
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Material {seed_material['material_id']} hard deleted successfully"
    )

    material = (
        db_session.query(Materials)
        .filter_by(material_id=seed_material["material_id"])
        .first()
    )
    assert material is None


def test_edit_material(client, jwt_token, seed_material, db_session):
    from app.database.models import Materials

    data = {"name": "Updated Material", "measurement_unit": "liters"}
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/materials/{str(seed_material['material_id'])}/edit",
        json=data,
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Material edited successfully"

    material = (
        db_session.query(Materials)
        .filter_by(material_id=seed_material["material_id"])
        .first()
    )
    assert material is not None
    assert material.name == "Updated Material"
    assert material.measurement_unit == "liters"


def test_get_all_materials(client, jwt_token, seed_material):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/materials/all", headers=headers)

    assert response.status_code == 200
    assert "materials" in response.json
    assert response.json["msg"] == "Materials found successfully"

    materials = response.json["materials"]
    assert any(
        material["material_id"] == str(seed_material["material_id"])
        for material in materials
    )
