from uuid import UUID

# ✅ Жёсткое удаление


def test_project_leader_can_hard_delete_own_schedule(client, jwt_token_leader, seed_project_schedule_own):
    """
    Проверяет, что project-leader может жёстко удалить своё расписание.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.delete(
        f"/project_schedules/{seed_project_schedule_own['project_schedule_id']}/delete/hard",
        headers=headers
    )
    assert response.status_code == 200
    assert response.json["msg"] == f"Project schedule {seed_project_schedule_own['project_schedule_id']} hard deleted successfully"


def test_project_leader_cannot_hard_delete_other_schedule(client, jwt_token_leader, seed_project_schedule_other, seed_other_leader):
    """
    Проверяет, что project-leader НЕ может удалить чужое расписание.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    response = client.delete(
        f"/project_schedules/{seed_project_schedule_other['project_schedule_id']}/delete/hard",
        headers=headers
    )
    assert response.status_code == 403
    assert response.json["msg"] == "Forbidden"


# ✅ Редактирование
def test_project_leader_can_edit_own_schedule(client, jwt_token_leader, seed_project_schedule_own):
    """
    Проверяет, что project-leader может редактировать своё расписание.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    data = {"quantity": 20}

    response = client.patch(
        f"/project_schedules/{seed_project_schedule_own['project_schedule_id']}/edit",
        json=data,
        headers=headers
    )
    assert response.status_code == 200
    assert response.json["msg"] == "Project schedule updated successfully"


def test_project_leader_cannot_edit_other_schedule(client, jwt_token_leader, seed_project_schedule_other):
    """
    Проверяет, что project-leader НЕ может редактировать чужое расписание.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}
    data = {"quantity": 20}

    response = client.patch(
        f"/project_schedules/{seed_project_schedule_other['project_schedule_id']}/edit",
        json=data,
        headers=headers
    )
    assert response.status_code == 403
    assert response.json["msg"] == "Forbidden"


# ✅ Проверяем, что project-leader не может назначить другого лидера
def test_project_leader_cannot_assign_other_leader_to_schedule(client, jwt_token_leader, seed_other_leader, seed_object, seed_leader, seed_work, seed_project_other):
    """
    Проверяет, что если project-leader пытается установить другого пользователя project_leader,
    то всё равно будет установлен его собственный user_id.
    """
    headers = {"Authorization": f"Bearer {jwt_token_leader}"}

    # Отправляем данные, где project_leader – другой пользователь
    data = {
        "work": seed_work['work_id'],  # Любая работа
        "project": seed_project_other['project_id'],
        "quantity": 1
    }

    response = client.post("/project_schedules/add",
                           json=data, headers=headers)

    # Проверяем, что запрос успешный
    assert response.status_code == 403
    assert response.json["msg"] == "You cannot add not your projects"
