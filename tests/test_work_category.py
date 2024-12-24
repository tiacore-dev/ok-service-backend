import pytest
from uuid import uuid4


@pytest.fixture
def works_categories_manager(db_session):
    from app.database.managers.works_managers import WorkCategoriesManager
    return WorkCategoriesManager(session=db_session)


@pytest.fixture
def seed_work_category(db_session):
    """
    Добавляет тестовую категорию работы в базу перед тестом и возвращает словарь.
    """
    from app.database.models import WorkCategories
    category = WorkCategories(
        work_category_id=uuid4(),
        name="Test Category"
    )
    db_session.add(category)
    db_session.commit()
    return category.to_dict()


def test_add_work_category(client, jwt_token, db_session):
    """
    Тест на добавление новой категории работы через API.
    """
    from app.database.models import WorkCategories

    data = {"name": "New Work Category"}
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/work_category/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New work category added successfully"

    # Проверяем, что категория добавлена в базу данных
    category = db_session.query(WorkCategories).filter_by(
        name="New Work Category").first()
    assert category is not None
    assert category.name == "New Work Category"


def test_view_work_category(client, jwt_token, seed_work_category):
    """
    Тест на просмотр данных категории работы через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/work_category/{str(seed_work_category['work_category_id'])}/view", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Work category found successfully"

    # Проверяем данные категории из ответа
    category_data = response.json["work_category"]
    assert category_data["work_category_id"] == str(
        seed_work_category["work_category_id"])
    assert category_data["name"] == seed_work_category["name"]


def test_soft_delete_work_category(client, jwt_token, seed_work_category, db_session):
    """
    Тест на мягкое удаление категории работы через API.
    """
    from app.database.models import WorkCategories

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/work_category/{str(seed_work_category['work_category_id'])}/delete/soft", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Work category {
        seed_work_category['work_category_id']} soft deleted successfully"

    # Проверяем, что категория помечена как удаленная в базе данных
    category = db_session.query(WorkCategories).filter_by(
        work_category_id=seed_work_category["work_category_id"]).first()
    assert category is not None
    assert category.deleted is True


def test_hard_delete_work_category(client, jwt_token, seed_work_category, db_session):
    """
    Тест на жесткое удаление категории работы через API.
    """
    from app.database.models import WorkCategories

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/work_category/{str(seed_work_category['work_category_id'])}/delete/hard", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Work category {
        seed_work_category['work_category_id']} hard deleted successfully"

    # Проверяем, что категория удалена из базы данных
    category = db_session.query(WorkCategories).filter_by(
        work_category_id=seed_work_category["work_category_id"]).first()
    assert category is None


def test_edit_work_category(client, jwt_token, seed_work_category, db_session):
    """
    Тест на редактирование данных категории работы через API.
    """
    from app.database.models import WorkCategories

    data = {"name": "Updated Work Category"}
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/work_category/{str(seed_work_category['work_category_id'])}/edit", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Work category edited successfully"

    # Проверяем, что данные категории обновлены в базе данных
    category = db_session.query(WorkCategories).filter_by(
        work_category_id=seed_work_category["work_category_id"]).first()
    assert category is not None
    assert category.name == "Updated Work Category"


def test_get_all_work_categories(client, jwt_token, seed_work_category):
    """
    Тест на получение всех категорий работ через API с фильтрацией.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/work_category/all", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Work categories found successfully"

    categories = response.json["work_categories"]
    assert len(categories) > 0

    # Проверяем, что созданная категория присутствует в списке
    category_data = next((c for c in categories if c["work_category_id"] == str(
        seed_work_category["work_category_id"])), None)
    assert category_data is not None
    assert category_data["name"] == seed_work_category["name"]
