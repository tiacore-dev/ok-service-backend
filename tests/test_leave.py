from uuid import UUID

import pytest


@pytest.fixture
def leaves_manager(db_session):
    from app.database.managers.leaves_manager import LeavesManager

    return LeavesManager(session=db_session)  # type: ignore


def test_add_leave_success(client, jwt_token, seed_user, seed_leader, db_session):
    from app.database.models import Leaves

    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {
        "user": seed_user["user_id"],
        "responsible": seed_leader["user_id"],
        "start_date": 20240201,
        "end_date": 20240205,
        "reason": "vacation",
        "comment": "Trip",
    }

    response = client.post("/leaves/add", json=payload, headers=headers)

    assert response.status_code == 200
    leave_id = response.json["leave_id"]

    leave = db_session.query(Leaves).filter_by(leave_id=UUID(leave_id)).first()
    assert leave is not None
    assert leave.reason.value == "vacation"
    assert str(leave.user_id) == seed_user["user_id"]


def test_add_leave_overlap(client, jwt_token, seed_leave, seed_user, seed_leader):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {
        "user": seed_user["user_id"],
        "responsible": seed_leader["user_id"],
        "start_date": 20240104,
        "end_date": 20240106,
        "reason": "sick_leave",
    }

    response = client.post("/leaves/add", json=payload, headers=headers)

    assert response.status_code == 409
    assert response.json["msg"] == "Leave overlaps with existing record"


def test_add_leave_conflict_with_shift(
    client, jwt_token, seed_shift_report, seed_leader
):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {
        "user": seed_shift_report["user"],
        "responsible": seed_leader["user_id"],
        "start_date": seed_shift_report["date"],
        "end_date": seed_shift_report["date"] + 1,
        "reason": "day_off",
    }

    response = client.post("/leaves/add", json=payload, headers=headers)

    assert response.status_code == 409
    assert response.json["msg"] == "Shift exists within the specified period"


def test_shift_creation_conflict_with_leave(
    client,
    jwt_token,
    seed_leave,
    seed_project,
    seed_work_price,
    seed_project_work_own,
):
    headers = {"Authorization": f"Bearer {jwt_token}"}

    payload = {
        "user": seed_leave["user"],
        "date": 20240103,
        "project": seed_project["project_id"],
        "signed": False,
        "details": [],
    }

    response = client.post("/shift_reports/add", json=payload, headers=headers)

    assert response.status_code == 409
    assert response.json["msg"] == "User has a leave during the requested date"
