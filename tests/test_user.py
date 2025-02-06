from uuid import uuid4, UUID
import json
from flask_jwt_extended import decode_token
import pytest


@pytest.fixture
def user_manager(db_session):
    from app.database.managers.user_manager import UserManager
    return UserManager(session=db_session)


@pytest.fixture
def seed_admin(db_session):
    """
    Добавляет тестового админа в базу перед тестом.
    """
    from app.database.models import Users
    user_id = uuid4()
    user = Users(
        user_id=user_id,
        login="admin",
        name="admin",
        role="admin",
        created_by=user_id,
        deleted=False
    )
    user.set_password('qweasdzcx')
    db_session.add(user)
    db_session.commit()
    return user.to_dict()


@pytest.fixture
def seed_user(db_session, test_app, jwt_token):
    """
    Добавляет тестового пользователя в базу перед тестом.
    """
    from app.database.models import Users

    with test_app.app_context():  # Оборачиваем в контекст приложения
        # Декодируем `jwt_token` и извлекаем `user_id`
        decoded_token = decode_token(jwt_token)
        # `sub` содержит JSON-строку
        token_identity = json.loads(decoded_token["sub"])
        token_user_id = token_identity["user_id"]  # Достаем `user_id`

    user = Users(
        user_id=uuid4(),
        login="test_user",
        name="Test User",
        role="admin",
        created_by=token_user_id,
        deleted=False
    )
    user.set_password('qweasdzcx')
    db_session.add(user)
    db_session.commit()
    return user.to_dict()


def test_add_user(client, jwt_token, db_session, test_app):
    """
    Тест на добавление нового пользователя через API.
    """
    from app.database.models import Users
    with test_app.app_context():  # Оборачиваем в контекст приложения
        # Декодируем `jwt_token` и извлекаем `user_id`
        decoded_token = decode_token(jwt_token)
        # `sub` содержит JSON-строку
        token_identity = json.loads(decoded_token["sub"])
        token_user_id = token_identity["user_id"]  # Достаем `user_id`
    # Данные для создания пользователя
    data = {
        "login": "test_user",
        "password": "securepassword",
        "name": "Test User",
        "role": "admin",
        "category": 1
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/users/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New user added successfully"

    # Проверяем, что пользователь добавлен в базу
    user = db_session.query(Users).filter_by(login="test_user").first()
    assert user is not None
    assert str(user.created_by) == token_user_id
    assert user.name == "Test User"
    assert user.role == "admin"
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
    assert user_data["role"] == 'admin'


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


def test_hard_delete_admin(client, jwt_token, seed_admin, db_session):
    """
    Тест на жесткое удаление пользователя.
    """
    from app.database.models import Users

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/users/{str(seed_admin['user_id'])}/delete/hard", headers=headers)

    assert response.status_code == 403
    assert response.json["msg"] == "You cannot delete admin"

    # Проверяем, что пользователь удален из базы
    user = db_session.query(Users).filter_by(
        user_id=UUID(seed_admin['user_id'])).first()
    assert user is not None


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
    assert user_data["role"] == 'admin'
