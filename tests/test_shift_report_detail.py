# Namespace for ShiftReportDetails

from uuid import UUID, uuid4
import pytest


@pytest.fixture
def seed_shift_report_detail(db_session, seed_shift_report, seed_work, seed_user):
    from app.database.models import ShiftReportDetails
    detail = ShiftReportDetails(
        shift_report_detail_id=uuid4(),
        shift_report=UUID(seed_shift_report['shift_report_id']),
        work=UUID(seed_work['work_id']),
        created_by=seed_user['user_id'],
        quantity=10.5,
        summ=105.0
    )
    db_session.add(detail)
    db_session.commit()
    return detail.to_dict()


def test_add_shift_report_detail(client, jwt_token, seed_shift_report, seed_work, seed_work_price):
    data = {
        "shift_report": seed_shift_report['shift_report_id'],
        "work": seed_work['work_id'],
        "quantity": 20.0,
        "summ": 200.0
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/shift_report_details/add",
                           json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New shift report detail added successfully"


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


def test_edit_shift_report_detail(client, jwt_token, seed_shift_report_detail):
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
        detail = session.query(ShiftReportDetails).filter_by(
            shift_report_detail_id=seed_shift_report_detail['shift_report_detail_id']).first()
        assert detail.quantity == 3.0


def test_delete_shift_report_detail(client, jwt_token, seed_shift_report_detail, db_session):
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
