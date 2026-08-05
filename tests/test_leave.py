from uuid import UUID, uuid4

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
        "start_date": seed_shift_report["date_start"],
        "end_date": seed_shift_report["date_end"] + 1,
        "reason": "day_off",
    }

    response = client.post("/leaves/add", json=payload, headers=headers)

    assert response.status_code == 200


def test_add_leave_conflicts_with_open_shift(
    client, jwt_token, seed_user, seed_leader, seed_project, db_session
):
    from app.database.models import ShiftReports

    report = ShiftReports(
        shift_report_id=uuid4(),
        user=UUID(seed_user["user_id"]),
        date=20240103,
        date_start=20240103,
        date_end=None,
        project=UUID(seed_project["project_id"]),
        created_by=UUID(seed_leader["user_id"]),
        signed=False,
        deleted=False,
    )
    report_id = report.shift_report_id
    db_session.add(report)
    db_session.commit()

    response = client.post(
        "/leaves/add",
        json={
            "user": seed_user["user_id"],
            "responsible": seed_leader["user_id"],
            "start_date": 20240103,
            "end_date": 20240103,
            "reason": "day_off",
        },
        headers={"Authorization": f"Bearer {jwt_token}"},
    )

    assert response.status_code == 409
    assert response.json["msg"] == "Shift exists within the specified period"


def test_add_leave_cancels_unstarted_shift_and_sets_leave_id(
    client, jwt_token, seed_user, seed_leader, seed_project, db_session
):
    from app.database.models import ShiftReports

    report = ShiftReports(
        shift_report_id=uuid4(),
        user=UUID(seed_user["user_id"]),
        date=20240103,
        date_start=None,
        date_end=None,
        project=UUID(seed_project["project_id"]),
        created_by=UUID(seed_leader["user_id"]),
        signed=False,
        deleted=False,
    )
    report_id = report.shift_report_id
    db_session.add(report)
    db_session.commit()

    response = client.post(
        "/leaves/add",
        json={
            "user": seed_user["user_id"],
            "responsible": seed_leader["user_id"],
            "start_date": 20240103,
            "end_date": 20240103,
            "reason": "day_off",
        },
        headers={"Authorization": f"Bearer {jwt_token}"},
    )

    assert response.status_code == 200
    saved_report = (
        db_session.query(ShiftReports)
        .populate_existing()
        .filter_by(shift_report_id=report_id)
        .one()
    )
    assert saved_report.deleted is True
    assert str(saved_report.leave_id) == response.json["leave_id"]


def test_edit_leave_cancels_newly_included_unstarted_shift(
    client, jwt_token, seed_leave, seed_project, seed_leader, db_session
):
    from app.database.models import ShiftReports

    report = ShiftReports(
        shift_report_id=uuid4(),
        user=UUID(seed_leave["user"]),
        date=20240104,
        date_start=None,
        date_end=None,
        project=UUID(seed_project["project_id"]),
        created_by=UUID(seed_leader["user_id"]),
        signed=False,
        deleted=False,
    )
    report_id = report.shift_report_id
    db_session.add(report)
    db_session.commit()

    response = client.patch(
        f"/leaves/{seed_leave['leave_id']}/edit",
        json={"end_date": 20240104},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )

    assert response.status_code == 200
    saved_report = (
        db_session.query(ShiftReports)
        .populate_existing()
        .filter_by(shift_report_id=report_id)
        .one()
    )
    assert saved_report.deleted is True
    assert str(saved_report.leave_id) == seed_leave["leave_id"]


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


def test_leave_reasons_list(client, jwt_token):
    headers = {"Authorization": f"Bearer {jwt_token}"}

    response = client.get("/leaves/reasons/all", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Leave reasons found successfully"

    reasons = response.json["reasons"]
    assert len(reasons) == 3

    expected = {
        "vacation": "Отпуск",
        "sick_leave": "Больничный",
        "day_off": "Отгул",
    }
    assert {item["reason_id"]: item["name"] for item in reasons} == expected
