import pytest


@pytest.fixture
def seed_object_status(db_session):
    """
    Добавляет тестовый статус объекта в базу перед тестом.
    """
    from app.database.models import ObjectStatuses
    from uuid import uuid4
    status = ObjectStatuses(
        object_status_id=str(uuid4()),
        name="Existing Status"
    )
    db_session.add(status)
    db_session.commit()

    # Возвращаем данные как словарь
    return {
        "object_status_id": status.object_status_id,
        "name": status.name
    }


def test_get_all_object_statuses(client, jwt_token, seed_object_status):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    params = {
        "name": "Ex"
    }
    response = client.get("/object_statuses/all",
                          query_string=params, headers=headers)

    assert response.status_code == 200
    assert "object_statuses" in response.json
    assert response.json["msg"] == "Object statuses found successfully"
    assert len(response.json["object_statuses"]) > 0

    # Проверяем, что тестовый статус присутствует в списке
    statuses = response.json["object_statuses"]
    assert any(s["object_status_id"] ==
               seed_object_status["object_status_id"] for s in statuses)
    assert any(s["name"] == seed_object_status["name"] for s in statuses)
