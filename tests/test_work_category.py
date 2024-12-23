import pytest
from uuid import uuid4


@pytest.fixture
def works_categories_manager(db_session):
    from app.database.managers.works_managers import WorksCategoriesManager
    return WorksCategoriesManager(session=db_session)


@pytest.fixture
def seed_work_category(db_session):
    from app.database.models import WorkCategories
    category = WorkCategories(
        work_category_id=uuid4(),
        name="Test Category"
    )
    db_session.add(category)
    db_session.commit()
    return category


def test_add_work_category(client, jwt_token):
    data = {"name": "New Work Category"}
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/work_category/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New work category added successfully"


def test_view_work_category(client, jwt_token, seed_work_category):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/work_category/{str(seed_work_category.work_category_id)}/view", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Work category found successfully"


def test_soft_delete_work_category(client, jwt_token, seed_work_category):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/work_category/{str(seed_work_category.work_category_id)}/delete/soft", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"""Work category {
        str(seed_work_category.work_category_id)} soft deleted successfully"""


def test_hard_delete_work_category(client, jwt_token, seed_work_category):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/work_category/{str(seed_work_category.work_category_id)}/delete/hard", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"""Work category {
        str(seed_work_category.work_category_id)} hard deleted successfully"""


def test_edit_work_category(client, jwt_token, seed_work_category):
    """
    Тест на редактирование данных категории работ через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    data = {"name": "Updated Work Category"}
    response = client.patch(
        f"/work_category/{str(seed_work_category.work_category_id)}/edit", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Work category edited successfully"

    # Проверяем, что данные категории обновлены
    from app.database.managers.works_managers import WorksCategoriesManager
    manager = WorksCategoriesManager()
    with manager.session_scope() as session:
        category = session.query(manager.model).filter_by(
            work_category_id=seed_work_category.work_category_id).first()
        assert category.name == "Updated Work Category"


def test_get_all_work_categories(client, jwt_token, seed_work_category):
    """
    Тест на получение всех категорий работ через API с фильтрацией.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/work_category/all", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Work categories found successfully"
    assert len(response.json["work_categories"]) > 0

    # Проверяем, что созданная категория присутствует в списке
    categories = response.json["work_categories"]
    assert any(c["work_category_id"] ==
               str(seed_work_category.work_category_id) for c in categories)
