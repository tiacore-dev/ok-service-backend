from uuid import uuid4
import pytest


@pytest.fixture
def objects_manager(db_session):
    from app.database.managers.objects_managers import ObjectsManager
    return ObjectsManager(session=db_session)


@pytest.fixture
def seed_object_status(db_session):
    """
    Добавляет тестовый статус объекта в базу перед тестом.
    """
    from app.database.models import ObjectStatuses
    status = ObjectStatuses(
        object_status_id=str(uuid4()),
        name="Active"
    )
    db_session.add(status)
    db_session.commit()
    return status.to_dict()


@pytest.fixture
def seed_object(db_session, seed_object_status):
    """
    Добавляет тестовый объект в базу перед тестом.
    """
    from app.database.models import Objects
    obj = Objects(
        object_id=uuid4(),
        name="Test Object",
        address="123 Test St",
        description="Test description",
        status=seed_object_status["object_status_id"],
        deleted=False
    )
    db_session.add(obj)
    db_session.commit()
    return obj.to_dict()


def test_add_object(client, jwt_token, db_session, seed_object_status):
    """
    Тест на добавление нового объекта через API.
    """
    from app.database.models import Objects

    data = {
        "name": "New Object",
        "address": "456 Test Ln",
        "description": "New description",
        "status": seed_object_status['object_status_id']
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/objects/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New object added successfully"

    # Проверяем, что объект добавлен в базу
    obj = db_session.query(Objects).filter_by(name="New Object").first()
    assert obj is not None
    assert obj.name == "New Object"
    assert obj.address == "456 Test Ln"
    assert obj.description == "New description"
    assert obj.status == seed_object_status['object_status_id']


def test_view_object(client, jwt_token, seed_object):
    """
    Тест на просмотр данных объекта через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/objects/{str(seed_object['object_id'])}/view", headers=headers)

    assert response.status_code == 200
    assert "object" in response.json
    assert response.json["msg"] == "Object found successfully"
    assert response.json["object"]["name"] == seed_object['name']
    assert response.json["object"]["address"] == seed_object['address']


def test_soft_delete_object(client, jwt_token, seed_object):
    """
    Тест на мягкое удаление объекта.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/objects/{str(seed_object['object_id'])}/delete/soft", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"""Object {
        str(seed_object['object_id'])} soft deleted successfully"""

    # Проверяем, что объект помечен как удаленный
    from app.database.managers.objects_managers import ObjectsManager
    objects_manager = ObjectsManager()
    with objects_manager.session_scope() as session:
        obj = session.query(objects_manager.model).filter_by(
            object_id=seed_object['object_id']).first()
        assert obj.deleted is True


def test_hard_delete_object(client, jwt_token, seed_object, db_session):
    """
    Тест на жесткое удаление объекта.
    """
    from app.database.models import Objects

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/objects/{str(seed_object['object_id'])}/delete/hard", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Object {
        str(seed_object['object_id'])} hard deleted successfully"

    # Проверяем, что объект удален из базы
    obj = db_session.query(Objects).filter_by(
        object_id=seed_object['object_id']).first()
    assert obj is None


def test_edit_object(client, jwt_token, seed_object):
    """
    Тест на редактирование данных объекта через API.
    """
    data = {
        "name": "Updated Object",
        "address": "789 Updated St",
        "description": "Updated description",
        "status": None  # Допустим, хотим убрать статус
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/objects/{str(seed_object['object_id'])}/edit", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Object edited successfully"

    # Проверяем обновленные данные в базе
    from app.database.managers.objects_managers import ObjectsManager
    objects_manager = ObjectsManager()
    with objects_manager.session_scope() as session:
        obj = session.query(objects_manager.model).filter_by(
            object_id=seed_object['object_id']).first()
        assert obj is not None
        assert obj.name == "Updated Object"
        assert obj.address == "789 Updated St"
        assert obj.description == "Updated description"


def test_get_all_objects(client, jwt_token, seed_object):
    """
    Тест на получение списка объектов через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/objects/all", headers=headers)

    assert response.status_code == 200
    assert "objects" in response.json
    assert response.json["msg"] == "Objects found successfully"
    assert len(response.json["objects"]) > 0

    # Проверяем, что тестовый объект присутствует в списке
    objects = response.json["objects"]
    assert any(o["object_id"] == str(seed_object['object_id'])
               for o in objects)
