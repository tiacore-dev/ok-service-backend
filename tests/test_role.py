import pytest
from uuid import uuid4

from app.database.models import ApiKeys, KeyPermissionTypeRelations, PermissionTypes


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


def test_get_all_roles_accepts_api_key_with_permission(client, db_session, seed_role):
    permission = (
        db_session.query(PermissionTypes).filter_by(code="roles-list").one_or_none()
    )
    if permission is None:
        permission = PermissionTypes(
            code="roles-list",
            description="GET /roles/all",
        )
        db_session.add(permission)
        db_session.flush()

    api_key = ApiKeys(name=f"roles-{uuid4().hex}", token=f"token-{uuid4().hex}")
    db_session.add(api_key)
    db_session.flush()
    db_session.add(
        KeyPermissionTypeRelations(
            api_key_id=api_key.api_key_id,
            permission_type_id=permission.permission_type_id,
        )
    )
    db_session.commit()

    response = client.get("/roles/all", headers={"API-Key": api_key.token})

    assert response.status_code == 200
    assert any(
        role["role_id"] == seed_role["role_id"] for role in response.json["roles"]
    )


def test_get_all_roles_rejects_api_key_without_permission(client, db_session):
    api_key = ApiKeys(name=f"roles-{uuid4().hex}", token=f"token-{uuid4().hex}")
    db_session.add(api_key)
    db_session.commit()

    response = client.get("/roles/all", headers={"API-Key": api_key.token})

    assert response.status_code == 403
