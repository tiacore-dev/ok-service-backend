# Tests for ProjectSchedules


def test_add_project_schedule(client, jwt_token_leader, seed_work, seed_project_own):
    """
    Test adding a new project schedule via API.
    """
    data = {
        "work": seed_work['work_id'],
        "project": seed_project_own['project_id'],
        "quantity": 200.0,
        "date": 20240101
    }
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.post("/project_schedules/add",
                           json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New project schedule added successfully"

    from app.database.models import ProjectSchedules
    with client.application.app_context():
        from app.database.db_globals import Session
        session = Session()
        schedule = session.query(ProjectSchedules).filter_by(
            quantity=200.0).first()
        assert str(
            schedule.project_schedule_id) == response.json['project_schedule_id']
        assert schedule is not None


def test_view_project_schedule(client, jwt_token_leader, seed_project_schedule_own, seed_work):
    """
    Test viewing a project schedule via API.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.get(
        f"/project_schedules/{str(seed_project_schedule_own['project_schedule_id'])}/view", headers=headers)

    assert response.status_code == 200
    assert "project_schedule" in response.json
    assert response.json["msg"] == "Project schedule found successfully"
    assert response.json["project_schedule"]["quantity"] == seed_project_schedule_own['quantity']
    assert response.json["project_schedule"]["work"] == seed_work['work_id']


def test_edit_project_schedule(client, jwt_token_leader, seed_project_schedule_own):
    """
    Test editing a project schedule via API.
    """
    data = {
        "quantity": 150.0,
        "date": 20240105
    }
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.patch(
        f"/project_schedules/{str(seed_project_schedule_own['project_schedule_id'])}/edit", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Project schedule updated successfully"
    assert response.json['project_schedule_id'] == seed_project_schedule_own['project_schedule_id']

    from app.database.models import ProjectSchedules
    with client.application.app_context():
        from app.database.db_globals import Session
        session = Session()
        schedule = session.query(ProjectSchedules).filter_by(
            project_schedule_id=seed_project_schedule_own['project_schedule_id']).first()
        assert schedule is not None
        assert schedule.quantity == 150.0
        assert schedule.date == 20240105


def test_hard_delete_project_schedule(client, jwt_token_leader, seed_project_schedule_own, db_session):
    """
    Test hard deleting a project schedule.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.delete(
        f"/project_schedules/{str(seed_project_schedule_own['project_schedule_id'])}/delete/hard", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Project schedule {
        str(seed_project_schedule_own['project_schedule_id'])} hard deleted successfully"
    assert response.json['project_schedule_id'] == seed_project_schedule_own['project_schedule_id']

    from app.database.models import ProjectSchedules
    obj = db_session.query(ProjectSchedules).filter_by(
        project_schedule_id=seed_project_schedule_own['project_schedule_id']).first()
    assert obj is None


def test_get_all_project_schedules(client, jwt_token_leader, seed_project_schedule_own):
    """
    Test fetching all project schedules via API.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.get("/project_schedules/all", headers=headers)

    assert response.status_code == 200
    assert "project_schedules" in response.json
    assert response.json["msg"] == "Project schedules found successfully"
    assert len(response.json["project_schedules"]) > 0

    schedules = response.json["project_schedules"]
    assert any(s["project_schedule_id"] == str(
        seed_project_schedule_own['project_schedule_id']) for s in schedules)
    assert schedules[0]["work"] is not None
