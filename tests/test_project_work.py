from uuid import uuid4, UUID
import pytest


@pytest.fixture
def seed_work(db_session):
    from app.database.models import Works
    work = Works(
        work_id=uuid4(),
        name="Test Work",
        category=None,
        measurement_unit="Unit",
        deleted=False
    )
    db_session.add(work)
    db_session.commit()
    return work.to_dict()


@pytest.fixture
def seed_object(db_session):
    """
    Добавляет тестовый объект в базу перед тестом.
    """
    from app.database.models import Objects
    obj = Objects(
        object_id=uuid4(),
        name="Test Object",
        address="123 Test St",
        description="Test description",
        status="active",
        deleted=False
    )
    db_session.add(obj)
    db_session.commit()
    obj_data = obj.to_dict()
    return obj_data


@pytest.fixture
def seed_user(db_session):
    """
    Add a test user to the database.
    """
    from app.database.models import Users
    user = Users(
        user_id=uuid4(),
        login="test_user",
        password_hash="test_hash",
        name="Test User",
        role="user",
        category=1,
        deleted=False
    )
    db_session.add(user)
    db_session.commit()
    return user.to_dict()


@pytest.fixture
def seed_project(db_session, seed_user, seed_object):
    """
    Add a test project to the database.
    """
    from app.database.models import Projects
    project = Projects(
        project_id=uuid4(),
        name="Test Project",
        object=UUID(seed_object['object_id']),
        project_leader=UUID(seed_user['user_id']),
        deleted=False
    )
    db_session.add(project)
    db_session.commit()
    return project.to_dict()


@pytest.fixture
def seed_project_work(db_session, seed_work, seed_project):
    from app.database.models import ProjectWorks
    project_work = ProjectWorks(
        project_work_id=uuid4(),
        project=seed_project['project_id'],
        work=seed_work["work_id"],
        quantity=100.0,
        summ=5000.0,
        signed=False
    )
    db_session.add(project_work)
    db_session.commit()
    project_work_data = project_work.to_dict()
    project_work_data["work"] = seed_work  # Добавляем вложенность
    return project_work_data


def test_add_project_work(client, jwt_token, db_session, seed_work, seed_project):
    """
    Тест на добавление нового ProjectWork через API.
    """
    from app.database.models import ProjectWorks

    data = {
        "project": seed_project['project_id'],
        "work": seed_work["work_id"],
        "quantity": 200.0,
        "summ": 10000.0,
        "signed": True
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/project_works/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New project work added successfully"

    project_work = db_session.query(ProjectWorks).filter_by(
        work=seed_work["work_id"]).first()
    assert project_work is not None
    assert str(
        project_work.project_work_id) == response.json['project_work_id']
    assert project_work.quantity == 200.0
    assert project_work.summ == 10000.0
    assert project_work.signed is True


def test_view_project_work(client, jwt_token, seed_project_work, seed_work):
    """
    Тест на просмотр данных ProjectWork через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/project_works/{str(seed_project_work['project_work_id'])}/view", headers=headers)

    assert response.status_code == 200
    assert "project_work" in response.json
    assert response.json["msg"] == "Project work found successfully"

    project_work_data = response.json["project_work"]
    assert project_work_data["project_work_id"] == str(
        seed_project_work["project_work_id"])
    assert project_work_data["quantity"] == seed_project_work["quantity"]
    assert project_work_data["summ"] == seed_project_work["summ"]
    assert project_work_data["signed"] == seed_project_work["signed"]

    assert project_work_data["work"] == seed_work["work_id"]


def test_soft_delete_project_work(client, jwt_token, seed_project_work):
    """
    Тест на мягкое удаление ProjectWork.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/project_works/{str(seed_project_work['project_work_id'])}/delete/soft", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Project work {
        seed_project_work['project_work_id']} soft deleted successfully"
    assert response.json['project_work_id'] == seed_project_work['project_work_id']


def test_hard_delete_project_work(client, jwt_token, seed_project_work, db_session):
    """
    Тест на жесткое удаление ProjectWork.
    """
    from app.database.models import ProjectWorks

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/project_works/{str(seed_project_work['project_work_id'])}/delete/hard", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Project work {
        seed_project_work['project_work_id']} hard deleted successfully"
    assert response.json['project_work_id'] == seed_project_work['project_work_id']

    project_work = db_session.query(ProjectWorks).filter_by(
        project_work_id=seed_project_work["project_work_id"]).first()
    assert project_work is None


def test_edit_project_work(client, jwt_token, seed_project_work, db_session):
    """
    Тест на редактирование данных ProjectWork через API.
    """
    from app.database.models import ProjectWorks

    data = {
        "quantity": 300.0,
        "summ": 15000.0,
        "signed": True
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/project_works/{str(seed_project_work['project_work_id'])}/edit", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Project work edited successfully"
    assert response.json['project_work_id'] == seed_project_work['project_work_id']

    project_work = db_session.query(ProjectWorks).filter_by(
        project_work_id=seed_project_work["project_work_id"]).first()
    assert project_work is not None
    assert project_work.quantity == 300.0
    assert project_work.summ == 15000.0
    assert project_work.signed is True


def test_get_all_project_works(client, jwt_token, seed_project_work, seed_work):
    """
    Тест на получение списка ProjectWorks через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/project_works/all", headers=headers)

    assert response.status_code == 200
    assert "project_works" in response.json
    assert response.json["msg"] == "Project works found successfully"

    project_works = response.json["project_works"]
    project_work_data = next((pw for pw in project_works if pw["project_work_id"] == str(
        seed_project_work["project_work_id"])), None)
    assert project_work_data is not None

    assert project_work_data["work"] == seed_work["work_id"]
