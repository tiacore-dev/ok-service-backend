from uuid import uuid4
import pytest


@pytest.fixture
def works_manager(db_session):
    from app.database.managers.works_managers import WorksManager
    return WorksManager(session=db_session)


@pytest.fixture
def seed_work_category(db_session):
    """
    Добавляет тестовую категорию работы в базу перед тестом.
    """
    from app.database.models import WorkCategories
    category = WorkCategories(
        work_category_id=uuid4(),
        name="Test Category",
        deleted=False
    )
    db_session.add(category)
    db_session.commit()
    return category.to_dict()


@pytest.fixture
def seed_work(db_session, seed_work_category):
    """
    Добавляет тестовую работу в базу перед тестом.
    """
    from app.database.models import Works
    work = Works(
        work_id=uuid4(),
        name="Test Work",
        category=seed_work_category['work_category_id'],
        measurement_unit="Unit",
        deleted=False
    )
    db_session.add(work)
    db_session.commit()
    return work.to_dict()


def test_add_work(client, jwt_token, seed_work_category, db_session):
    """
    Тест на добавление новой работы через API с проверкой базы данных.
    """
    from app.database.models import Works

    data = {
        "name": "New Work",
        "category": seed_work_category['work_category_id'],
        "measurement_unit": "New Unit"
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/works/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New work added successfully"

    # Проверяем, что работа добавлена в базу
    work = db_session.query(Works).filter_by(name="New Work").first()
    assert work is not None
    assert work.name == "New Work"
    assert str(work.category) == seed_work_category['work_category_id']
    assert work.measurement_unit == "New Unit"


def test_view_work(client, jwt_token, seed_work):
    """
    Тест на просмотр данных работы через API с проверкой соответствия базе данных.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/works/{str(seed_work['work_id'])}/view", headers=headers)

    assert response.status_code == 200
    assert "work" in response.json
    assert response.json["msg"] == "Work found successfully"

    # Проверяем данные из ответа
    work_data = response.json["work"]
    assert work_data["work_id"] == str(seed_work['work_id'])
    assert work_data["name"] == seed_work['name']
    assert work_data["category"] == str(seed_work['category'])
    assert work_data["measurement_unit"] == seed_work['measurement_unit']


def test_soft_delete_work(client, jwt_token, seed_work, db_session):
    """
    Тест на мягкое удаление работы с проверкой в базе данных.
    """
    from app.database.models import Works

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/works/{str(seed_work['work_id'])}/delete/soft", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Work {
        seed_work['work_id']} soft deleted successfully"

    # Проверяем, что работа помечена как удаленная в базе
    work = db_session.query(Works).filter_by(
        work_id=seed_work['work_id']).first()
    assert work is not None
    assert work.deleted is True


def test_hard_delete_work(client, jwt_token, seed_work, db_session):
    """
    Тест на жесткое удаление работы с проверкой отсутствия в базе данных.
    """
    from app.database.models import Works

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/works/{str(seed_work['work_id'])}/delete/hard", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Work {
        seed_work['work_id']} hard deleted successfully"

    # Проверяем, что работа удалена из базы
    work = db_session.query(Works).filter_by(
        work_id=seed_work['work_id']).first()
    assert work is None


def test_edit_work(client, jwt_token, seed_work, db_session):
    """
    Тест на редактирование данных работы через API с проверкой изменений в базе данных.
    """
    from app.database.models import Works

    data = {
        "name": "Updated Work",
        "measurement_unit": "Updated Unit"
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/works/{str(seed_work['work_id'])}/edit", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Work edited successfully"

    # Проверяем обновленные данные в базе
    work = db_session.query(Works).filter_by(
        work_id=seed_work['work_id']).first()
    assert work is not None
    assert work.name == "Updated Work"
    assert work.measurement_unit == "Updated Unit"


def test_get_all_works(client, jwt_token, seed_work):
    """
    Тест на получение списка работ через API с проверкой присутствия в базе данных.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/works/all", headers=headers)

    assert response.status_code == 200
    assert "works" in response.json
    assert response.json["msg"] == "Works found successfully"

    # Проверяем, что тестовая работа присутствует в списке
    works = response.json["works"]
    assert any(work["work_id"] == str(seed_work['work_id']) for work in works)
