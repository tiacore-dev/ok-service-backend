import pytest


def test_add_shift_report_material(
    client, jwt_token_user, seed_shift_report, seed_project_material, db_session
):
    from app.database.models import ShiftReportMaterials

    data = {
        "shift_report": seed_shift_report["shift_report_id"],
        "project_material": seed_project_material["project_material_id"],
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
            project_material=seed_project_material["project_material_id"],
        )
        .first()
    )
    assert record is not None
    assert (
        str(record.shift_report_material_id)
        == response.json["shift_report_material_id"]
    )
    assert str(record.shift_report) == seed_shift_report["shift_report_id"]
    assert str(record.project_material) == seed_project_material["project_material_id"]
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
    assert record["project_material"] == str(
        seed_shift_report_material["project_material"]
    )
    assert "material" not in record


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


@pytest.mark.parametrize(
    "value", ["00000000-0000-0000-0000-000000000001", "", "invalid"]
)
def test_removed_material_filter_returns_400_without_listing(
    client,
    jwt_token_user,
    monkeypatch,
    value,
):
    from app.web.shift_report_materials import routes

    def unexpected_repository():
        pytest.fail("An obsolete filter must be rejected before listing records")

    monkeypatch.setattr(routes, "_repository", unexpected_repository)
    response = client.get(
        "/shift_report_materials/all",
        query_string={"material": value},
        headers={"Authorization": f"Bearer {jwt_token_user}"},
    )
    assert response.status_code == 400
    assert response.json["error"] == {
        "material": ["Filter 'material' was removed; use 'project_material'."]
    }


def test_project_material_link_response_filter_and_delete_conflict(
    client,
    jwt_token_admin,
    db_session,
    seed_shift_report,
    seed_material,
    seed_work,
    seed_user,
    seed_material_pcs,
    seed_project_own,
    jwt_token_user,
):
    from uuid import UUID

    from app.database.models import ProjectMaterials, ProjectWorks, ShiftReportDetails

    project_work = ProjectWorks(
        project=UUID(seed_shift_report["project"]),
        work=UUID(seed_work["work_id"]),
        quantity=10,
        created_by=UUID(seed_user["user_id"]),
    )
    db_session.add(project_work)
    db_session.flush()
    detail = ShiftReportDetails(
        shift_report=UUID(seed_shift_report["shift_report_id"]),
        project_work=project_work.project_work_id,
        work=UUID(seed_work["work_id"]),
        quantity=3,
        summ=0,
        created_by=UUID(seed_user["user_id"]),
    )
    material = ProjectMaterials(
        project=UUID(seed_shift_report["project"]),
        project_work=project_work.project_work_id,
        material=UUID(seed_material["material_id"]),
        quantity=10,
        price=7,
        summ=70,
        created_by=UUID(seed_user["user_id"]),
    )
    db_session.add_all([detail, material])
    db_session.commit()
    material_id = str(material.project_material_id)
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}
    response = client.post(
        "/shift_report_materials/add",
        headers=headers,
        json={
            "shift_report": seed_shift_report["shift_report_id"],
            "project_material": material_id,
            "quantity": 3,
            "shift_report_detail": str(detail.shift_report_detail_id),
        },
    )
    assert response.status_code == 200
    actual_id = response.json["shift_report_material_id"]
    view = client.get(f"/shift_report_materials/{actual_id}/view", headers=headers)
    assert view.status_code == 200
    assert view.json["shift_report_material"]["project_material"] == material_id
    listed = client.get(
        "/shift_report_materials/all",
        headers=headers,
        query_string={"project_material": material_id},
    )
    assert listed.status_code == 200
    assert [
        item["shift_report_material_id"]
        for item in listed.json["shift_report_materials"]
    ] == [actual_id]
    from uuid import uuid4

    empty = client.get(
        "/shift_report_materials/all",
        headers=headers,
        query_string={"project_material": str(uuid4())},
    )
    assert empty.status_code == 200
    assert empty.json["shift_report_materials"] == []
    invalid = client.get(
        "/shift_report_materials/all",
        headers=headers,
        query_string={"project_material": "invalid"},
    )
    assert invalid.status_code == 400
    for changes in (
        {"project_work": None},
        {"material": seed_material_pcs["material_id"]},
        {"project": seed_project_own["project_id"]},
    ):
        edited = client.patch(
            f"/project_materials/{material_id}/edit", headers=headers, json=changes
        )
        assert edited.status_code == 409
    allowed = client.patch(
        f"/project_materials/{material_id}/edit",
        headers=headers,
        json={"price": 9, "quantity": 12, "project_material_name": "Updated"},
    )
    assert allowed.status_code == 200
    forbidden = client.patch(
        f"/project_materials/{material_id}/edit",
        headers={"Authorization": f"Bearer {jwt_token_user}"},
        json={"quantity": 2},
    )
    assert forbidden.status_code == 403
    deleted = client.delete(
        f"/project_materials/{material_id}/delete/hard", headers=headers
    )
    assert deleted.status_code == 409
    catalog_delete = client.delete(
        f"/materials/{seed_material['material_id']}/delete/hard", headers=headers
    )
    assert catalog_delete.status_code == 409
    assert (
        client.get(
            f"/shift_report_materials/{actual_id}/view", headers=headers
        ).status_code
        == 200
    )


def test_shift_material_swagger_exposes_project_material(client):
    response = client.get("/swagger.json")
    assert response.status_code == 200
    definitions = response.json["definitions"]
    assert "project_material" in definitions["ShiftReportMaterial"]["properties"]
    for name in (
        "ShiftReportMaterial",
        "ShiftReportMaterialCreate",
        "ShiftReportMaterialEdit",
    ):
        assert "material" not in definitions[name]["properties"]
        assert "project_material" in definitions[name]["properties"]
    assert "project_material" in definitions["ShiftReportMaterialCreate"]["required"]
    parameters = response.json["paths"]["/shift_report_materials/all"]["get"][
        "parameters"
    ]
    assert any(item["name"] == "project_material" for item in parameters)

    assert all(item["name"] != "material" for item in parameters)


@pytest.mark.parametrize(
    "value", [None, "invalid", "00000000-0000-0000-0000-000000000001", "omitted"]
)
def test_create_requires_existing_non_null_project_material(
    client,
    jwt_token_user,
    seed_shift_report,
    value,
):
    data = {"shift_report": seed_shift_report["shift_report_id"], "quantity": 2}
    if value != "omitted":
        data["project_material"] = value
    response = client.post(
        "/shift_report_materials/add",
        json=data,
        headers={"Authorization": f"Bearer {jwt_token_user}"},
    )
    assert response.status_code == 400


def test_edit_rejects_null_project_material(
    client, jwt_token_user, seed_shift_report_material
):
    response = client.patch(
        f"/shift_report_materials/{seed_shift_report_material['shift_report_material_id']}/edit",
        json={"project_material": None},
        headers={"Authorization": f"Bearer {jwt_token_user}"},
    )
    assert response.status_code == 400


def test_piece_quantity_is_validated_through_project_material_on_create_and_patch(
    client,
    jwt_token_user,
    db_session,
    seed_shift_report,
    seed_material_pcs,
    seed_user,
):
    from uuid import UUID

    from app.database.models import ProjectMaterials

    row = ProjectMaterials(
        project=UUID(seed_shift_report["project"]),
        material=UUID(seed_material_pcs["material_id"]),
        quantity=10,
        created_by=UUID(seed_user["user_id"]),
    )
    db_session.add(row)
    db_session.commit()
    headers = {"Authorization": f"Bearer {jwt_token_user}"}
    created = client.post(
        "/shift_report_materials/add",
        headers=headers,
        json={
            "shift_report": seed_shift_report["shift_report_id"],
            "project_material": str(row.project_material_id),
            "quantity": 2.7,
        },
    )
    assert created.status_code == 200
    actual_id = created.json["shift_report_material_id"]
    view_path = f"/shift_report_materials/{actual_id}/view"
    edit_path = f"/shift_report_materials/{actual_id}/edit"
    assert (
        client.get(view_path, headers=headers).json["shift_report_material"]["quantity"]
        == 2
    )
    assert (
        client.patch(edit_path, headers=headers, json={"quantity": 3.9}).status_code
        == 200
    )
    assert (
        client.get(view_path, headers=headers).json["shift_report_material"]["quantity"]
        == 3
    )
    assert (
        client.patch(edit_path, headers=headers, json={"quantity": 0.9}).status_code
        == 400
    )
    assert (
        client.get(view_path, headers=headers).json["shift_report_material"]["quantity"]
        == 3
    )
