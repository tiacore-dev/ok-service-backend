from uuid import UUID


def test_project_leader_can_soft_delete_own_work(client, jwt_token_leader, seed_project_work_own):
    """
    Проверяет, что project-leader может мягко удалить свою работу.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.patch(
        f"/project_works/{seed_project_work_own['project_work_id']}/delete/soft",
        headers=headers
    )
    assert response.status_code == 200
    assert response.json["msg"] == f"Project work {seed_project_work_own['project_work_id']} soft deleted successfully"


def test_project_leader_cannot_soft_delete_other_work(client, jwt_token_leader, seed_project_work_other, seed_other_leader):
    """
    Проверяет, что project-leader НЕ может удалить чужую работу.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.patch(
        f"/project_works/{seed_project_work_other['project_work_id']}/delete/soft",
        headers=headers
    )
    assert response.status_code == 403
    assert response.json["msg"] == "Forbidden"


def test_project_leader_can_hard_delete_own_work(client, jwt_token_leader, seed_project_work_own):
    """
    Проверяет, что project-leader может жёстко удалить свою работу.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.delete(
        f"/project_works/{seed_project_work_own['project_work_id']}/delete/hard",
        headers=headers
    )
    assert response.status_code == 200
    assert response.json["msg"] == f"Project work {seed_project_work_own['project_work_id']} hard deleted successfully"


def test_project_leader_can_edit_own_work(client, jwt_token_leader, seed_project_work_own):
    """
    Проверяет, что project-leader может редактировать свою работу.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    data = {"summ": "1"}

    response = client.patch(
        f"/project_works/{seed_project_work_own['project_work_id']}/edit",
        json=data,
        headers=headers
    )
    assert response.status_code == 200
    assert response.json["msg"] == "Project work edited successfully"


def test_project_leader_cannot_edit_other_work(client, jwt_token_leader, seed_project_work_other):
    """
    Проверяет, что project-leader НЕ может редактировать чужую работу.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    data = {"name": "Hacked Work Name"}

    response = client.patch(
        f"/project_works/{seed_project_work_other['project_work_id']}/edit",
        json=data,
        headers=headers
    )
    assert response.status_code == 403
    assert response.json["msg"] == "Forbidden"


def test_project_leader_cannot_assign_other_leader(client, jwt_token_leader, seed_other_leader, seed_object, seed_leader):
    """
    Проверяет, что если project-leader пытается установить другого пользователя project_leader,
    то всё равно будет установлен его собственный user_id.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}

    # Отправляем данные, где project_leader – другой пользователь
    data = {
        "name": "Test Unauthorized Project",
        "object": seed_object['object_id'],
        # Чужой ID (должен проигнорироваться)
        "project_leader": seed_other_leader["user_id"]
    }

    response = client.post("/projects/add", json=data, headers=headers)

    # Проверяем, что запрос успешный
    assert response.status_code == 200
    assert response.json["msg"] == "New project added successfully"

    # Получаем ID нового проекта
    project_id = response.json["project_id"]

    # Проверяем в базе, что project_leader – тот, кто делал запрос (а не чужой)
    from app.database.models import Projects
    with client.application.app_context():
        from app.database.db_globals import Session
        session = Session()
        try:
            project = session.query(Projects).filter_by(
                project_id=UUID(project_id)).first()
            assert project is not None
            assert str(
                project.project_leader) == seed_leader["user_id"]
            assert str(
                project.project_leader) != seed_other_leader["user_id"]
        finally:
            session.close()
