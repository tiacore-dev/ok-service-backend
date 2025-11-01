from uuid import uuid4

from app.database.models import ShiftReports


# ✅ Тест создания Shift Report
def test_create_shift_report(
    client, jwt_token_user, db_session, seed_user, seed_project, seed_admin
):
    headers = {"Authorization": f"Bearer {jwt_token_user}"}
    data = {
        "user": seed_admin["user_id"],
        "date": 20240102,
        "date_start": 20240102,
        "date_end": 20240102,
        "project": seed_project["project_id"],
    }

    response = client.post("/shift_reports/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New shift report added successfully"

    report_id = response.json["shift_report_id"]
    report = db_session.query(ShiftReports).filter_by(shift_report_id=report_id).first()

    assert report is not None
    assert str(report.user) == seed_user["user_id"]  # Должен быть его user_id
    assert report.date_start == 20240102
    assert report.date_end == 20240102


# ✅ Тест просмотра отчёта (user видит только свои)
def test_view_shift_report(
    client, jwt_token_user, jwt_token_admin, seed_shift_report, seed_admin
):
    headers_user = {"Authorization": f"Bearer {jwt_token_user}"}
    headers_admin = {"Authorization": f"Bearer {jwt_token_admin}"}

    # Пользователь может видеть свой отчёт
    response = client.get(
        f"/shift_reports/{seed_shift_report['shift_report_id']}/view",
        headers=headers_user,
    )
    assert response.status_code == 200

    # Админ может видеть всё
    response = client.get(
        f"/shift_reports/{seed_shift_report['shift_report_id']}/view",
        headers=headers_admin,
    )
    assert response.status_code == 200

    # Если отчёт не существует
    response = client.get(f"/shift_reports/{uuid4()}/view", headers=headers_user)
    assert response.status_code == 404


# ✅ Тест редактирования (user не может редактировать чужие или подписанные)
def test_edit_shift_report(
    client, jwt_token_user, db_session, seed_shift_report, seed_project
):
    headers_user = {"Authorization": f"Bearer {jwt_token_user}"}
    # headers_admin = {"Authorization": f"Bearer {jwt_token_admin}"}

    data = {"project": seed_project["project_id"]}

    # Пользователь может редактировать свой отчёт
    response = client.patch(
        f"/shift_reports/{seed_shift_report['shift_report_id']}/edit",
        json=data,
        headers=headers_user,
    )
    assert response.status_code == 200

    # Если отчёт подписан → нельзя редактировать
    db_session.query(ShiftReports).filter_by(
        shift_report_id=seed_shift_report["shift_report_id"]
    ).update({"signed": True})
    db_session.commit()

    response = client.patch(
        f"/shift_reports/{seed_shift_report['shift_report_id']}/edit",
        json=data,
        headers=headers_user,
    )
    assert response.status_code == 403


# ✅ Тест мягкого удаления
def test_soft_delete_shift_report(
    client, jwt_token_user, db_session, seed_shift_report
):
    headers = {"Authorization": f"Bearer {jwt_token_user}"}

    response = client.patch(
        f"/shift_reports/{seed_shift_report['shift_report_id']}/delete/soft",
        headers=headers,
    )
    assert response.status_code == 200

    report = (
        db_session.query(ShiftReports)
        .filter_by(shift_report_id=seed_shift_report["shift_report_id"])
        .first()
    )
    assert report.deleted is True


# ✅ Тест жёсткого удаления
def test_hard_delete_shift_report(
    client, jwt_token_admin, db_session, seed_shift_report
):
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}

    response = client.delete(
        f"/shift_reports/{seed_shift_report['shift_report_id']}/delete/hard",
        headers=headers,
    )
    assert response.status_code == 200

    report = (
        db_session.query(ShiftReports)
        .filter_by(shift_report_id=seed_shift_report["shift_report_id"])
        .first()
    )
    assert report is None


# ✅ Тест получения всех отчётов (user → только свои, admin → все)
def test_get_all_shift_reports(
    client, jwt_token_user, jwt_token_admin, seed_shift_report
):
    headers_user = {"Authorization": f"Bearer {jwt_token_user}"}
    headers_admin = {"Authorization": f"Bearer {jwt_token_admin}"}

    response = client.get("/shift_reports/all", headers=headers_user)
    assert response.status_code == 200
    assert len(response.json["shift_reports"]) == 1  # Только свои

    response = client.get("/shift_reports/all", headers=headers_admin)
    assert response.status_code == 200
    assert len(response.json["shift_reports"]) >= 1  # Админ видит всё
