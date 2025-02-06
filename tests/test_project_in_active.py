from uuid import uuid4, UUID
import pytest


@pytest.fixture
def seed_user(db_session):
    """
    Добавляет тестового пользователя в базу перед тестом.
    """
    from app.database.models import Users
    user_id = uuid4()
    user = Users(
        user_id=user_id,
        login="test_user",
        name="Test User",
        role="user",
        created_by=user_id,
        deleted=False
    )
    user.set_password('qweasdzcx')
    db_session.add(user)
    db_session.commit()
    return user.to_dict()


@pytest.fixture
def seed_active_object(db_session, seed_user):
    """
    Добавляет тестовый объект со статусом 'active' в базу перед тестом.
    """
    from app.database.models import Objects
    obj = Objects(
        object_id=uuid4(),
        name="Active Object",
        address="123 Active St",
        description="Active object",
        status="active",
        created_by=seed_user['user_id'],
        deleted=False
    )
    db_session.add(obj)
    db_session.commit()
    return obj.to_dict()


@pytest.fixture
def seed_inactive_object(db_session, seed_user):
    """
    Добавляет тестовый объект со статусом 'waiting' в базу перед тестом.
    """
    from app.database.models import Objects
    obj = Objects(
        object_id=uuid4(),
        name="Inactive Object",
        address="456 Inactive St",
        description="Inactive object",
        status="waiting",
        created_by=seed_user['user_id'],
        deleted=False
    )
    db_session.add(obj)
    db_session.commit()
    return obj.to_dict()


@pytest.fixture
def seed_project_active(db_session, seed_active_object, seed_user):
    """
    Добавляет тестовый проект с активным объектом.
    """
    from app.database.models import Projects
    project = Projects(
        project_id=uuid4(),
        name="Project With Active Object",
        object=UUID(seed_active_object["object_id"]),
        project_leader=UUID(seed_user["user_id"]),
        deleted=False
    )
    db_session.add(project)
    db_session.commit()
    return project.to_dict()


@pytest.fixture
def seed_project_inactive(db_session, seed_inactive_object, seed_user):
    """
    Добавляет тестовый проект с объектом, у которого статус 'inactive'.
    """
    from app.database.models import Projects
    project = Projects(
        project_id=uuid4(),
        name="Project With Inactive Object",
        object=UUID(seed_inactive_object["object_id"]),
        project_leader=UUID(seed_user["user_id"]),
        deleted=False
    )
    db_session.add(project)
    db_session.commit()
    return project.to_dict()


def test_admin_sees_all_projects(client, jwt_token_admin, seed_project_active, seed_project_inactive):
    """
    Тест на то, что админ видит ВСЕ проекты, независимо от статуса объекта.
    """
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}

    response = client.get("/projects/all", headers=headers)
    assert response.status_code == 200
    projects = response.json["projects"]

    # Админ должен видеть оба проекта (активный и неактивный)
    assert any(str(p["object"]) == str(seed_project_active["object"])
               for p in projects)  # Активный объект
    assert any(str(p["object"]) == str(seed_project_inactive["object"])
               for p in projects)  # Неактивный объект


def test_user_sees_only_active_projects(client, jwt_token_user, seed_project_active, seed_project_inactive):
    """
    Тест на то, что обычный user видит только проекты с активными объектами.
    """
    headers = {"Authorization": f"Bearer {jwt_token_user}"}

    response = client.get("/projects/all", headers=headers)
    assert response.status_code == 200
    projects = response.json["projects"]

    # Пользователь не должен видеть проект с неактивным объектом
    assert all(str(p["object"]) != str(seed_project_inactive["object"])
               for p in projects)

    # Пользователь должен видеть только проекты, у которых у объектов статус 'active'
    assert any(str(p["object"]) == str(seed_project_active["object"])
               for p in projects)
