def test_add_shift_report_material(
    client, jwt_token_user, seed_shift_report, seed_material, db_session
):
    from app.database.models import ShiftReportMaterials

    data = {
        "shift_report": seed_shift_report["shift_report_id"],
        "material": seed_material["material_id"],
        "quantity": 4.5,
    }
    headers = {"Authorization": f"Bearer {jwt_token_user}"}
    response = client.post("/shift_report_materials/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Shift report material added successfully"

    record = (
        db_session.query(ShiftReportMaterials)
        .filter_by(
            shift_report=seed_shift_report["shift_report_id"],
            material=seed_material["material_id"],
        )
        .first()
    )
    assert record is not None
    assert str(record.shift_report_material_id) == response.json[
        "shift_report_material_id"
    ]
    assert str(record.shift_report) == seed_shift_report["shift_report_id"]
    assert str(record.material) == seed_material["material_id"]
    assert float(record.quantity) == 4.5


def test_view_shift_report_material(client, jwt_token_user, seed_shift_report_material):
    headers = {"Authorization": f"Bearer {jwt_token_user}"}
    response = client.get(
        f"/shift_report_materials/{str(seed_shift_report_material['shift_report_material_id'])}/view",
        headers=headers,
    )

    assert response.status_code == 200
    assert "shift_report_material" in response.json
    assert response.json["msg"] == "Shift report material found successfully"

    record = response.json["shift_report_material"]
    assert record["shift_report_material_id"] == str(
        seed_shift_report_material["shift_report_material_id"]
    )
    assert record["shift_report"] == str(seed_shift_report_material["shift_report"])
    assert record["material"] == str(seed_shift_report_material["material"])


def test_hard_delete_shift_report_material(
    client, jwt_token_user, seed_shift_report_material, db_session
):
    from app.database.models import ShiftReportMaterials

    headers = {"Authorization": f"Bearer {jwt_token_user}"}
    response = client.delete(
        f"/shift_report_materials/{str(seed_shift_report_material['shift_report_material_id'])}/delete/hard",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Shift report material {seed_shift_report_material['shift_report_material_id']} hard deleted successfully"
    )

    record = (
        db_session.query(ShiftReportMaterials)
        .filter_by(
            shift_report_material_id=seed_shift_report_material[
                "shift_report_material_id"
            ]
        )
        .first()
    )
    assert record is None


def test_edit_shift_report_material(
    client, jwt_token_user, seed_shift_report_material, db_session
):
    from app.database.models import ShiftReportMaterials

    data = {"quantity": 8.0}
    headers = {"Authorization": f"Bearer {jwt_token_user}"}
    response = client.patch(
        f"/shift_report_materials/{str(seed_shift_report_material['shift_report_material_id'])}/edit",
        json=data,
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Shift report material edited successfully"

    record = (
        db_session.query(ShiftReportMaterials)
        .filter_by(
            shift_report_material_id=seed_shift_report_material[
                "shift_report_material_id"
            ]
        )
        .first()
    )
    assert record is not None
    assert float(record.quantity) == 8.0


def test_get_all_shift_report_materials(
    client, jwt_token_user, seed_shift_report_material
):
    headers = {"Authorization": f"Bearer {jwt_token_user}"}
    response = client.get("/shift_report_materials/all", headers=headers)

    assert response.status_code == 200
    assert "shift_report_materials" in response.json
    assert response.json["msg"] == "Shift report materials found successfully"

    records = response.json["shift_report_materials"]
    assert any(
        rec["shift_report_material_id"]
        == str(seed_shift_report_material["shift_report_material_id"])
        for rec in records
    )
