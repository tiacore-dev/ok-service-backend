def test_add_project_material(client, jwt_token, seed_project, seed_material, db_session):
    from app.database.models import ProjectMaterials

    data = {
        "project": seed_project["project_id"],
        "material": seed_material["material_id"],
        "quantity": 3.25,
        "price": 10.0,
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/project_materials/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Project material added successfully"

    record = (
        db_session.query(ProjectMaterials)
        .filter_by(project=seed_project["project_id"], material=seed_material["material_id"])
        .first()
    )
    assert record is not None
    assert str(record.project_material_id) == response.json["project_material_id"]
    assert str(record.project) == seed_project["project_id"]
    assert str(record.material) == seed_material["material_id"]
    assert float(record.quantity) == 3.25
    assert float(record.price) == 10.0
    assert float(record.summ) == 32.5


def test_view_project_material(client, jwt_token, seed_project_material):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/project_materials/{str(seed_project_material['project_material_id'])}/view",
        headers=headers,
    )

    assert response.status_code == 200
    assert "project_material" in response.json
    assert response.json["msg"] == "Project material found successfully"

    record = response.json["project_material"]
    assert record["project_material_id"] == str(seed_project_material["project_material_id"])
    assert record["project"] == str(seed_project_material["project"])
    assert record["material"] == str(seed_project_material["material"])
    assert "price" in record
    assert "summ" in record


def test_hard_delete_project_material(client, jwt_token, seed_project_material, db_session):
    from app.database.models import ProjectMaterials

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/project_materials/{str(seed_project_material['project_material_id'])}/delete/hard",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Project material {seed_project_material['project_material_id']} hard deleted successfully"
    )

    record = (
        db_session.query(ProjectMaterials)
        .filter_by(project_material_id=seed_project_material["project_material_id"])
        .first()
    )
    assert record is None


def test_edit_project_material(client, jwt_token, seed_project_material, db_session):
    from app.database.models import ProjectMaterials

    data = {"quantity": 6.0, "price": 12.0}
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/project_materials/{str(seed_project_material['project_material_id'])}/edit",
        json=data,
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Project material edited successfully"

    record = (
        db_session.query(ProjectMaterials)
        .filter_by(project_material_id=seed_project_material["project_material_id"])
        .first()
    )
    assert record is not None
    assert float(record.quantity) == 6.0
    assert float(record.price) == 12.0
    assert float(record.summ) == 72.0

    view_response = client.get(
        f"/project_materials/{str(seed_project_material['project_material_id'])}/view",
        headers=headers,
    )
    assert view_response.status_code == 200
    assert view_response.json["project_material"]["price"] == 12.0
    assert view_response.json["project_material"]["summ"] == 72.0

    clear_response = client.patch(
        f"/project_materials/{str(seed_project_material['project_material_id'])}/edit",
        json={"price": None},
        headers=headers,
    )
    assert clear_response.status_code == 200
    cleared_view_response = client.get(
        f"/project_materials/{str(seed_project_material['project_material_id'])}/view",
        headers=headers,
    )
    assert cleared_view_response.json["project_material"]["price"] is None
    assert cleared_view_response.json["project_material"]["summ"] is None


def test_get_all_project_materials(client, jwt_token, seed_project_material):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/project_materials/all", headers=headers)

    assert response.status_code == 200
    assert "project_materials" in response.json
    assert response.json["msg"] == "Project materials found successfully"

    records = response.json["project_materials"]
    assert any(
        rec["project_material_id"]
        == str(seed_project_material["project_material_id"])
        for rec in records
    )
    material_record = next(
        rec
        for rec in records
        if rec["project_material_id"]
        == str(seed_project_material["project_material_id"])
    )
    assert "price" in material_record
    assert "summ" in material_record
