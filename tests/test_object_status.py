import pytest


@pytest.fixture
def seed_object_status(db_session):
    """
    Добавляет тестовый статус объекта в базу перед тестом.
    """
    from app.database.models import ObjectStatuses
    status = ObjectStatuses(
        object_status_id="existing_status",
        name="Existing Status"
    )
    db_session.add(status)
    db_session.commit()
    return status


def test_add_object_status(client, jwt_token, db_session):
    """
    Тест на добавление нового статуса объекта через API.
    """
    from app.database.models import ObjectStatuses

    data = {
        "object_status_id": "new_status",
        "name": "New Status"
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/object_statuses/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New object status added successfully"

    # Проверяем, что статус добавлен в базу
    status = db_session.query(ObjectStatuses).filter_by(
        object_status_id="new_status").first()
    assert status is not None
    assert status.name == "New Status"


def test_view_object_status(client, jwt_token, seed_object_status):
    """
    Тест на просмотр статуса объекта через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/object_statuses/{seed_object_status.object_status_id}/view", headers=headers)

    assert response.status_code == 200
    assert "object_status" in response.json
    assert response.json["msg"] == "Object status found successfully"
    assert response.json["object_status"]["name"] == seed_object_status.name


def test_soft_delete_object_status(client, jwt_token, seed_object_status, db_session):
    """
    Тест на мягкое удаление статуса объекта.
    """
    from app.database.models import ObjectStatuses

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/object_statuses/{seed_object_status.object_status_id}/delete/soft", headers=headers
    )

    assert response.status_code == 200
    assert response.json["msg"] == f"Object status {
        seed_object_status.object_status_id} soft deleted successfully"

    # Проверяем, что статус помечен как удаленный
    status = db_session.query(ObjectStatuses).filter_by(
        object_status_id=seed_object_status.object_status_id).first()
    assert status.deleted is True


def test_hard_delete_object_status(client, jwt_token, seed_object_status, db_session):
    """
    Тест на жесткое удаление статуса объекта.
    """
    from app.database.models import ObjectStatuses

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/object_statuses/{str(seed_object_status.object_status_id)}/delete/hard", headers=headers
    )

    assert response.status_code == 200
    assert response.json["msg"] == f"Object status {
        seed_object_status.object_status_id} hard deleted successfully"

    # Проверяем, что статус удален из базы
    status = db_session.query(ObjectStatuses).filter_by(
        object_status_id=seed_object_status.object_status_id).first()
    assert status is None


def test_edit_object_status(client, jwt_token, seed_object_status, db_session):
    """
    Тест на редактирование статуса объекта через API.
    """
    from app.database.models import ObjectStatuses

    data = {
        "name": "Updated Status"
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/object_statuses/{str(seed_object_status.object_status_id)}/edit", json=data, headers=headers
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Object status edited successfully"

    # Проверяем обновленные данные в базе
    status = db_session.query(ObjectStatuses).filter_by(
        object_status_id=seed_object_status.object_status_id).first()
    assert status.name == "Updated Status"


def test_get_all_object_statuses(client, jwt_token, seed_object_status):
    """
    Тест на получение списка статусов объектов через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/object_statuses/all", headers=headers)

    assert response.status_code == 200
    assert "object_statuses" in response.json
    assert response.json["msg"] == "Object statuses found successfully"
    assert len(response.json["object_statuses"]) > 0

    # Проверяем, что тестовый статус присутствует в списке
    statuses = response.json["object_statuses"]
    assert any(s["object_status_id"] ==
               seed_object_status.object_status_id for s in statuses)
