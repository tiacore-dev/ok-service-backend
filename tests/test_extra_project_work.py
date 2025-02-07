import json
import pytest
from uuid import uuid4, UUID
from flask_jwt_extended import create_access_token


@pytest.fixture
def seed_other_leader(db_session):
    """
    Добавляет второго тестового пользователя, который будет лидером другого проекта.
    """
    from app.database.models import Users
    user_id = uuid4()
    user = Users(
        user_id=user_id,
        login="test_other_leader",
        name="Test Other Leader",
        role="project-leader",
        created_by=user_id,
        deleted=False
    )
    user.set_password('qweasdzcx')
    db_session.add(user)
    db_session.commit()
    return user.to_dict()


@pytest.fixture
def jwt_token_other_leader(test_app, seed_other_leader):
    """
    Генерирует JWT токен для второго project-leader.
    """
    with test_app.app_context():
        token_data = {
            "login": seed_other_leader['login'],
            "role": seed_other_leader['role'],
            "user_id": seed_other_leader['user_id']
        }
        return create_access_token(identity=json.dumps(token_data))


@pytest.fixture
def seed_project_own(db_session, seed_leader, seed_object):
    """Создаёт проект, которым владеет seed_leader."""
    from app.database.models import Projects
    project_id = uuid4()
    project = Projects(
        project_id=project_id,
        name="Test Project Own",
        object=UUID(seed_object['object_id']),
        project_leader=UUID(seed_leader["user_id"]),
        created_by=UUID(seed_leader["user_id"]),
        deleted=False
    )
    db_session.add(project)
    db_session.commit()
    return project.to_dict()


@pytest.fixture
def seed_project_other(db_session, seed_other_leader, seed_object):
    """Создаёт проект, которым владеет seed_other_leader."""
    from app.database.models import Projects
    project_id = uuid4()
    project = Projects(
        project_id=project_id,
        name="Test Project Other",
        object=UUID(seed_object['object_id']),
        project_leader=UUID(seed_other_leader["user_id"]),
        created_by=UUID(seed_other_leader["user_id"]),
        deleted=False
    )
    db_session.add(project)
    db_session.commit()
    return project.to_dict()


@pytest.fixture
def seed_project_work_own(db_session, seed_project_own, seed_work):
    """Создаёт работу внутри своего проекта."""
    from app.database.models import ProjectWorks
    project_work_id = uuid4()
    project_work = ProjectWorks(
        project_work_id=project_work_id,
        work=UUID(seed_work['work_id']),
        project=UUID(seed_project_own["project_id"]),
        summ=0,
        quantity=0,
        created_by=UUID(seed_project_own["created_by"]),
        signed=False
    )
    db_session.add(project_work)
    db_session.commit()
    return project_work.to_dict()


@pytest.fixture
def seed_project_work_other(db_session, seed_project_other, seed_work):
    """Создаёт работу внутри чужого проекта."""
    from app.database.models import ProjectWorks
    project_work_id = uuid4()
    project_work = ProjectWorks(
        project_work_id=project_work_id,
        work=UUID(seed_work['work_id']),
        project=UUID(seed_project_other["project_id"]),
        summ=0,
        quantity=0,
        created_by=UUID(seed_project_other["created_by"]),
        signed=False
    )
    db_session.add(project_work)
    db_session.commit()
    return project_work.to_dict()


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
        project = session.query(Projects).filter_by(
            project_id=UUID(project_id)).first()
        assert project is not None
        assert str(
            project.project_leader) == seed_leader["user_id"]
        assert str(
            project.project_leader) != seed_other_leader["user_id"]
