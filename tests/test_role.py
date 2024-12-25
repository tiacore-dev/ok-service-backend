import pytest


@pytest.fixture
def seed_role(db_session):
    """
    Добавляет тестовый статус объекта в базу перед тестом.
    """
    from app.database.models import Roles
    from uuid import uuid4
    role = Roles(
        role_id=str(uuid4()),
        name="Existing role"
    )
    db_session.add(role)
    db_session.commit()

    # Возвращаем данные как словарь
    return {
        "role_id": role.role_id,
        "name": role.name
    }


def test_get_all_roles(client, jwt_token, seed_role):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/roles/all", headers=headers)

    assert response.status_code == 200
    assert "roles" in response.json
    assert response.json["msg"] == "Roles found successfully"
    assert len(response.json["roles"]) > 0

    # Проверяем, что тестовый статус присутствует в списке
    roles = response.json["roles"]
    assert any(r["role_id"] ==
               seed_role["role_id"] for r in roles)
    assert any(r["name"] == seed_role["name"] for r in roles)
