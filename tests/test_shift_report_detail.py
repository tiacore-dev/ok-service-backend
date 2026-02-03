# Namespace for ShiftReportDetails

from uuid import UUID, uuid4
import pytest


@pytest.fixture
def seed_shift_report_detail(
    db_session,
    seed_shift_report,
    seed_work,
    seed_user,
    seed_project_work_own,
    seed_work_material_relation,
    seed_work_material_relation_pcs,
):
    from app.database.models import ShiftReportDetails
    from app.database.managers.shift_reports_managers import ShiftReportsDetailsManager

    detail = ShiftReportDetails(
        shift_report_detail_id=uuid4(),
        project_work=UUID(seed_project_work_own["project_work_id"]),
        shift_report=UUID(seed_shift_report["shift_report_id"]),
        work=UUID(seed_work["work_id"]),
        created_by=seed_user["user_id"],
        quantity=10.5,
        summ=105.0,
    )
    db_session.add(detail)
    db_session.flush()

    ShiftReportsDetailsManager._sync_shift_report_materials(
        db_session, detail, seed_user["user_id"]
    )

    db_session.commit()
    return detail.to_dict()


def test_add_shift_report_detail(
    client,
    jwt_token,
    seed_shift_report,
    seed_work,
    seed_work_price,
    seed_project_work_own,
    seed_work_material_relation,
    seed_work_material_relation_pcs,
    db_session,
):
    data = {
        "shift_report": seed_shift_report['shift_report_id'],
        "project_work": seed_project_work_own['project_work_id'],
        "work": seed_work['work_id'],
        "quantity": 20.0
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/shift_report_details/add",
                           json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New shift report detail added successfully"

    from app.database.models import ShiftReportMaterials

    detail_id = response.json["shift_report_detail_id"]
    records = db_session.query(ShiftReportMaterials).filter_by(
        shift_report_detail=detail_id
    ).all()
    assert len(records) == 2
    quantities = {str(r.material): float(r.quantity) for r in records}
    assert quantities[seed_work_material_relation["material"]] == 20.0 * float(
        seed_work_material_relation["quantity"]
    )
    assert quantities[seed_work_material_relation_pcs["material"]] == int(
        20.0 * float(seed_work_material_relation_pcs["quantity"])
    )


def test_view_shift_report_detail(client, jwt_token, seed_shift_report_detail):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"""/shift_report_details/{
            seed_shift_report_detail['shift_report_detail_id']}/view""",
        headers=headers)

    assert response.status_code == 200
    assert "shift_report_detail" in response.json
    assert response.json["msg"] == "Shift report detail found successfully"
    assert response.json["shift_report_detail"]["quantity"] == seed_shift_report_detail['quantity']
    assert response.json["shift_report_detail"]["summ"] == seed_shift_report_detail['summ']
    assert response.json["shift_report_detail"]["project_work"][
        "project_work_id"
    ] == seed_shift_report_detail["project_work"]["project_work_id"]


def test_edit_shift_report_detail(
    client,
    jwt_token,
    seed_shift_report_detail,
    db_session,
    seed_work_material_relation,
    seed_work_material_relation_pcs,
):
    data = {
        "quantity": 3.0
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(f"/shift_report_details/{seed_shift_report_detail['shift_report_detail_id']}/edit",
                            json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Shift report detail updated successfully"

    with client.application.app_context():
        from app.database.db_globals import Session
        session = Session()
        from app.database.models import ShiftReportDetails
        try:
            detail = session.query(ShiftReportDetails).filter_by(
                shift_report_detail_id=seed_shift_report_detail['shift_report_detail_id']).first()
            assert detail.quantity == 3.0
        finally:
            session.close()

    from app.database.models import ShiftReportMaterials
    records = db_session.query(ShiftReportMaterials).filter_by(
        shift_report_detail=seed_shift_report_detail["shift_report_detail_id"]
    ).all()
    assert len(records) == 2
    quantities = {str(r.material): float(r.quantity) for r in records}
    assert quantities[seed_work_material_relation["material"]] == 3.0 * float(
        seed_work_material_relation["quantity"]
    )
    assert quantities[seed_work_material_relation_pcs["material"]] == int(
        3.0 * float(seed_work_material_relation_pcs["quantity"])
    )


def test_delete_shift_report_detail(
    client,
    jwt_token,
    seed_shift_report_detail,
    db_session,
):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(f"""/shift_report_details/{
                             seed_shift_report_detail['shift_report_detail_id']}/delete/hard""",
                             headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Shift report detail {
        seed_shift_report_detail['shift_report_detail_id']} deleted successfully"

    from app.database.models import ShiftReportDetails
    detail = db_session.query(ShiftReportDetails).filter_by(
        shift_report_detail_id=seed_shift_report_detail['shift_report_detail_id']).first()
    assert detail is None

    from app.database.models import ShiftReportMaterials
    records = db_session.query(ShiftReportMaterials).filter_by(
        shift_report_detail=seed_shift_report_detail["shift_report_detail_id"]
    ).all()
    assert records == []


def test_get_all_shift_report_details_with_filters(client, jwt_token, seed_shift_report_detail, seed_shift_report, seed_work):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    params = {
        "shift_report": seed_shift_report['shift_report_id'],
        "work": seed_work['work_id']
    }
    response = client.get("/shift_report_details/all",
                          query_string=params, headers=headers)

    assert response.status_code == 200
    assert "shift_report_details" in response.json
    assert response.json["msg"] == "Shift report details found successfully"

    details = response.json["shift_report_details"]
    assert len(details) > 0
    assert any(detail["shift_report_detail_id"] ==
               seed_shift_report_detail['shift_report_detail_id'] for detail in details)


def test_post_all_shift_report_details_by_ids(client, jwt_token, seed_shift_reports, seed_shift_report, seed_shift_report_detail):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    shift_report_ids = [r["shift_report_id"] for r in seed_shift_reports]
    shift_report_ids.append(seed_shift_report['shift_report_id'])
    response = client.post(
        "/shift_report_details/all-by-reports",
        json={"shift_report_ids": shift_report_ids},
        headers=headers
    )

    assert response.status_code == 200
    data = response.json

    assert "shift_report_details" in data
    assert data["msg"] == "Shift report details found successfully"

    details = data["shift_report_details"]
    assert isinstance(details, list)
    assert len(details) >= 1
    assert any(detail["shift_report"]
               in shift_report_ids for detail in details)
