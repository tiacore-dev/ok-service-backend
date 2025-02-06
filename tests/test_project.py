from uuid import uuid4
import json
from flask_jwt_extended import decode_token
import pytest


@pytest.fixture
def projects_manager(db_session):
    from app.database.managers.projects_managers import ProjectsManager
    return ProjectsManager(session=db_session)


def test_add_project(client, jwt_token, db_session, seed_user, seed_object, test_app):
    """
    Тест на добавление нового проекта через API.
    """
    with test_app.app_context():  # Оборачиваем в контекст приложения
        # Декодируем `jwt_token` и извлекаем `user_id`
        decoded_token = decode_token(jwt_token)
        # `sub` содержит JSON-строку
        token_identity = json.loads(decoded_token["sub"])
        token_user_id = token_identity["user_id"]  # Достаем `user_id`

    data = {
        "name": "New Project",
        "object": seed_object['object_id'],
        "project_leader": seed_user['user_id']
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/projects/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New project added successfully"
    assert response.json['project_id'] != None

    # Проверяем, что проект добавлен в базу
    from app.database.models import Projects
    project = db_session.query(Projects).filter_by(name="New Project").first()
    assert project is not None
    assert str(project.project_id) == response.json['project_id']
    assert str(project.created_by) == token_user_id
    assert project.name == "New Project"
    assert str(project.object) == seed_object['object_id']
    assert str(project.project_leader) == seed_user['user_id']


def test_view_project(client, jwt_token, seed_project, seed_user, seed_object):
    """
    Тест на просмотр данных проекта через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/projects/{str(seed_project['project_id'])}/view", headers=headers)

    assert response.status_code == 200
    assert "project" in response.json
    assert response.json["msg"] == "Project found successfully"

    project_data = response.json["project"]
    assert project_data["project_id"] == str(seed_project["project_id"])
    assert project_data["name"] == seed_project["name"]

    # Проверяем вложенность object
    assert project_data["object"] == seed_object["object_id"]

    # Проверяем вложенность project_leader
    assert project_data["project_leader"] == seed_user["user_id"]


def test_soft_delete_project(client, jwt_token, seed_project):
    """
    Тест на мягкое удаление проекта.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/projects/{str(seed_project['project_id'])}/delete/soft", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Project {
        seed_project['project_id']} soft deleted successfully"
    assert response.json['project_id'] == seed_project['project_id']

    # Проверяем, что проект помечен как удаленный
    from app.database.models import Projects
    from app.database.managers.projects_managers import ProjectsManager
    projects_manager = ProjectsManager()
    with projects_manager.session_scope() as session:
        project = session.query(Projects).filter_by(
            project_id=seed_project['project_id']).first()
        assert project.deleted is True


def test_hard_delete_project(client, jwt_token, seed_project, db_session):
    """
    Тест на жесткое удаление проекта.
    """
    from app.database.models import Projects

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/projects/{str(seed_project['project_id'])}/delete/hard", headers=headers)
    assert response.json['project_id'] == seed_project['project_id']

    assert response.status_code == 200
    assert response.json["msg"] == f"Project {
        seed_project['project_id']} hard deleted successfully"

    # Проверяем, что проект удален из базы
    project = db_session.query(Projects).filter_by(
        project_id=seed_project['project_id']).first()
    assert project is None


def test_edit_project(client, jwt_token, seed_project):
    """
    Тест на редактирование данных проекта через API.
    """
    data = {
        "name": "Updated Project"
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/projects/{str(seed_project['project_id'])}/edit", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Project edited successfully"
    assert response.json['project_id'] == seed_project['project_id']

    # Проверяем обновленные данные в базе
    from app.database.models import Projects
    from app.database.managers.projects_managers import ProjectsManager
    projects_manager = ProjectsManager()
    with projects_manager.session_scope() as session:
        project = session.query(Projects).filter_by(
            project_id=seed_project['project_id']).first()
        assert project.name == "Updated Project"


def test_get_all_projects(client, jwt_token, seed_project, seed_user, seed_object):
    """
    Тест на получение списка проектов через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/projects/all", headers=headers)

    assert response.status_code == 200
    assert "projects" in response.json
    assert response.json["msg"] == "Projects found successfully"

    projects = response.json["projects"]
    project_data = next((p for p in projects if p["project_id"] == str(
        seed_project["project_id"])), None)
    assert project_data is not None

    # Проверяем вложенность object
    assert project_data["object"] == seed_object["object_id"]

    # Проверяем вложенность project_leader
    assert project_data["project_leader"] == seed_user["user_id"]
