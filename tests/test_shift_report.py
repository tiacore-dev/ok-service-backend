# Tests for ShiftReports
import logging
from uuid import UUID, uuid4

logger = logging.getLogger("ok_service")


def test_add_shift_report(
    client,
    jwt_token,
    seed_user,
    seed_project,
    seed_shift_report_detail,
    seed_work_price,
    seed_project_work_own,
):
    """
    Test adding a new shift report via API.
    """
    data = {
        "user": seed_user["user_id"],
        "date": 20240102,
        "date_start": 20240102,
        "date_end": 20240102,
        "project": seed_project["project_id"],
        "signed": True,
        "lng_start": 37.618,
        "ltd_start": 55.756,
        "lng_end": 37.619,
        "ltd_end": 55.757,
        "distance_start": 12.5,
        "distance_end": 18.75,
        "comment": "Test shift report comment",
        "details": [
            {
                "work": seed_shift_report_detail["work"],
                "summ": seed_shift_report_detail["summ"],
                "quantity": seed_shift_report_detail["quantity"],
                "project_work": seed_project_work_own["project_work_id"],
            }
        ],
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/shift_reports/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New shift report added successfully"

    from app.database.models import ShiftReports

    with client.application.app_context():
        from app.database.db_globals import Session

        session = Session()
        report = session.query(ShiftReports).filter_by(date=20240102).first()
        assert report is not None
        assert str(report.user) == seed_user["user_id"]
        assert str(report.project) == seed_project["project_id"]
        assert report.signed is True
        assert report.date_start == 20240102
        assert report.date_end == 20240102
        assert report.lng_start == 37.618
        assert report.ltd_start == 55.756
        assert report.lng_end == 37.619
        assert report.ltd_end == 55.757
        assert report.distance_start == 12.5
        assert report.distance_end == 18.75
        assert report.comment == "Test shift report comment"


def test_view_shift_report(
    client, jwt_token, seed_shift_report, seed_user, seed_project
):
    """
    Test viewing a shift report via API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/shift_reports/{str(seed_shift_report['shift_report_id'])}/view",
        headers=headers,
    )

    assert response.status_code == 200
    assert "shift_report" in response.json
    assert response.json["msg"] == "Shift report found successfully"
    assert response.json["shift_report"]["user"] == seed_user["user_id"]
    assert response.json["shift_report"]["project"] == seed_project["project_id"]
    assert response.json["shift_report"]["date"] == seed_shift_report["date"]
    assert (
        response.json["shift_report"]["date_start"] == seed_shift_report["date_start"]
    )
    assert response.json["shift_report"]["date_end"] == seed_shift_report["date_end"]
    assert response.json["shift_report"]["signed"] == seed_shift_report["signed"]
    assert response.json["shift_report"]["lng_start"] == seed_shift_report["lng_start"]
    assert response.json["shift_report"]["ltd_start"] == seed_shift_report["ltd_start"]
    assert response.json["shift_report"]["lng_end"] == seed_shift_report["lng_end"]
    assert response.json["shift_report"]["ltd_end"] == seed_shift_report["ltd_end"]
    assert (
        response.json["shift_report"]["distance_start"]
        == seed_shift_report["distance_start"]
    )
    assert (
        response.json["shift_report"]["distance_end"]
        == seed_shift_report["distance_end"]
    )
    assert response.json["shift_report"]["comment"] == seed_shift_report["comment"]


def test_soft_delete_shift_report(client, jwt_token, seed_shift_report):
    """
    Test soft deleting a shift report via API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/shift_reports/{str(seed_shift_report['shift_report_id'])}/delete/soft",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Shift report {
            str(seed_shift_report['shift_report_id'])
        } soft deleted successfully"
    )

    from app.database.models import ShiftReports

    with client.application.app_context():
        from app.database.db_globals import Session

        session = Session()
        report = (
            session.query(ShiftReports)
            .filter_by(shift_report_id=seed_shift_report["shift_report_id"])
            .first()
        )
        assert report is not None
        assert report.deleted is True


def test_hard_delete_shift_report(client, jwt_token, seed_shift_report, db_session):
    """
    Test hard deleting a shift report.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/shift_reports/{str(seed_shift_report['shift_report_id'])}/delete/hard",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Shift report {
            str(seed_shift_report['shift_report_id'])
        } hard deleted successfully"
    )

    from app.database.models import ShiftReports

    obj = (
        db_session.query(ShiftReports)
        .filter_by(shift_report_id=seed_shift_report["shift_report_id"])
        .first()
    )
    assert obj is None


def test_edit_shift_report(client, jwt_token, seed_shift_report):
    """
    Test editing a shift report via API.
    """
    data = {
        "date": 20240103,
        "signed": True,
        "lng_start": 40.0,
        "ltd_start": 50.0,
        "lng_end": 41.0,
        "ltd_end": 51.0,
        "distance_start": 22.0,
        "distance_end": 24.0,
        "comment": "Updated comment",
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/shift_reports/{str(seed_shift_report['shift_report_id'])}/edit",
        json=data,
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Shift report updated successfully"

    from app.database.models import ShiftReports

    with client.application.app_context():
        from app.database.db_globals import Session

        session = Session()
        report = (
            session.query(ShiftReports)
            .filter_by(shift_report_id=UUID(seed_shift_report["shift_report_id"]))
            .first()
        )
        assert report is not None
        assert report.date == 20240103
        assert report.date_start == seed_shift_report["date_start"]
        assert report.date_end == seed_shift_report["date_end"]
        assert report.signed is True
        assert report.lng_start == 40.0
        assert report.ltd_start == 50.0
        assert report.lng_end == 41.0
        assert report.ltd_end == 51.0
        assert report.distance_start == 22.0
        assert report.distance_end == 24.0
        assert report.comment == "Updated comment"


def test_get_all_shift_reports_with_filters(
    client, jwt_token, seed_shift_report, seed_user, seed_project
):
    """
    Test fetching all shift reports with filters via API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    allowed_users = [seed_user["user_id"], str(uuid4())]
    allowed_projects = [seed_project["project_id"], str(uuid4())]
    params = [
        ("user", allowed_users[0]),
        ("user", allowed_users[1]),
        ("date_start_from", seed_shift_report["date_start"]),
        ("date_start_to", seed_shift_report["date_start"]),
        ("project", allowed_projects[0]),
        ("project", allowed_projects[1]),
        ("deleted", False),
    ]
    logger.info(f"Отправляемые параметры: {params}")
    response = client.get("/shift_reports/all", query_string=params, headers=headers)

    assert response.status_code == 200
    assert "shift_reports" in response.json
    assert response.json["msg"] == "Shift reports found successfully"

    shift_reports = response.json["shift_reports"]
    assert len(shift_reports) > 0
    assert all(report["user"] in allowed_users for report in shift_reports)
    assert all(report["project"] in allowed_projects for report in shift_reports)
    target_report = next(
        report
        for report in shift_reports
        if report["shift_report_id"] == seed_shift_report["shift_report_id"]
    )
    assert target_report["user"] == seed_user["user_id"]
    assert target_report["project"] == seed_project["project_id"]
    assert target_report["date"] == seed_shift_report["date"]
    assert target_report["date_start"] == seed_shift_report["date_start"]
    assert target_report["date_end"] == seed_shift_report["date_end"]
    assert target_report["signed"] == seed_shift_report["signed"]
    assert target_report["lng_start"] == seed_shift_report["lng_start"]
    assert target_report["ltd_start"] == seed_shift_report["ltd_start"]
    assert target_report["lng_end"] == seed_shift_report["lng_end"]
    assert target_report["ltd_end"] == seed_shift_report["ltd_end"]
    assert target_report["distance_start"] == seed_shift_report["distance_start"]
    assert target_report["distance_end"] == seed_shift_report["distance_end"]
    assert target_report["comment"] == seed_shift_report["comment"]


def test_edit_shift_report_conflict_with_leave(
    client, jwt_token, seed_shift_report, seed_leave
):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    data = {
        "date": seed_leave["start_date"],
        "date_start": seed_leave["start_date"],
        "date_end": seed_leave["start_date"],
    }

    response = client.patch(
        f"/shift_reports/{seed_shift_report['shift_report_id']}/edit",
        json=data,
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json["msg"] == "Shift date intersects with existing leave"
