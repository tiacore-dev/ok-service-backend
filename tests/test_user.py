from uuid import uuid4, UUID
import pytest


@pytest.fixture
def user_manager(db_session):
    from app.database.managers.user_manager import UserManager
    return UserManager(session=db_session)


@pytest.fixture
def seed_user(db_session):
    """
    Добавляет тестового пользователя в базу перед тестом.
    """
    from app.database.models import Users
    user = Users(
        user_id=uuid4(),
        login="existing_user",
        name="Existing User",
        role='user',
        category=1,
        deleted=False
    )
    user.set_password("hashedpassword")
    db_session.add(user)
    db_session.commit()
    user_data = user.to_dict()
    return user_data


def test_add_user(client, jwt_token, db_session):
    """
    Тест на добавление нового пользователя через API.
    """
    from app.database.models import Users

    # Данные для создания пользователя
    data = {
        "login": "test_user",
        "password": "securepassword",
        "name": "Test User",
        "role": "user",
        "category": 1
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/users/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New user added successfully"

    # Проверяем, что пользователь добавлен в базу
    user = db_session.query(Users).filter_by(login="test_user").first()
    assert user is not None
    assert user.name == "Test User"
    assert user.role == "user"
    assert user.category == 1


def test_view_user(client, jwt_token, seed_user):
    """
    Тест на просмотр данных пользователя через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/users/{str(seed_user['user_id'])}/view", headers=headers)

    assert response.status_code == 200
    assert "user" in response.json
    assert response.json["msg"] == "User found successfully"

    user_data = response.json["user"]
    assert user_data["user_id"] == str(seed_user["user_id"])
    assert user_data["name"] == seed_user["name"]
    assert user_data["login"] == seed_user["login"]

    # Проверяем вложенность роли
    role_data = user_data["role"]
    assert role_data["role_id"] == 'user'
    assert role_data["name"] == 'Пользователь'


def test_soft_delete_user(client, jwt_token, seed_user):
    """
    Тест на мягкое удаление пользователя.
    """

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/users/{str(seed_user['user_id'])}/delete/soft", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"""User {
        str(seed_user['user_id'])} soft deleted successfully"""

    # Проверяем, что пользователь помечен как удаленный
    from app.database.managers.user_manager import UserManager
    user_manager = UserManager()
    with user_manager.session_scope() as session:
        user = session.query(user_manager.model).filter_by(
            user_id=UUID(seed_user['user_id'])).first()
        assert user.deleted is True


def test_hard_delete_user(client, jwt_token, seed_user, db_session):
    """
    Тест на жесткое удаление пользователя.
    """
    from app.database.models import Users

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/users/{str(seed_user['user_id'])}/delete/hard", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"""User {
        str(seed_user['user_id'])} hard deleted successfully"""

    # Проверяем, что пользователь удален из базы
    user = db_session.query(Users).filter_by(
        user_id=UUID(seed_user['user_id'])).first()
    assert user is None


def test_edit_user(client, jwt_token, seed_user):
    """
    Тест на редактирование данных пользователя через API.
    """
    # Данные для обновления пользователя
    data = {
        "login": "updated_user",
        "password": "newpassword",
        "name": "Updated User",
        "role": "admin",
        "category": 2
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/users/{str(seed_user['user_id'])}/edit", json=data, headers=headers
    )

    # Проверяем успешность запроса
    assert response.status_code == 200
    assert response.json["msg"] == "User edited successfully"

    # Повторно извлекаем объект пользователя из базы через UserManager
    from app.database.managers.user_manager import UserManager
    user_manager = UserManager()
    with user_manager.session_scope() as session:
        user = session.query(user_manager.model).filter_by(
            user_id=UUID(seed_user['user_id'])).first()

        # Проверяем обновленные данные
        assert user is not None
        assert user.login == "updated_user"
        assert user.name == "Updated User"
        assert user.role == "admin"
        assert user.category == 2


def test_get_all_users(client, jwt_token, seed_user):
    """
    Тест на получение списка пользователей через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/users/all", headers=headers)

    assert response.status_code == 200
    assert "users" in response.json
    assert response.json["msg"] == "Users found successfully"
    assert len(response.json["users"]) > 0

    # Проверяем, что тестовый пользователь присутствует в списке
    users = response.json["users"]
    user_data = next(
        (u for u in users if u["user_id"] == str(seed_user["user_id"])), None)
    assert user_data is not None

    # Проверяем вложенность роли
    role_data = user_data["role"]
    assert role_data["role_id"] == 'user'
    assert role_data["name"] == 'Пользователь'
