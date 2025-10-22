import pytest


@pytest.fixture
def work_prices_manager(db_session):
    from app.database.managers.works_managers import WorkPricesManager

    return WorkPricesManager(session=db_session)  # type: ignore


def test_add_work_price(client, jwt_token, seed_work, db_session):
    """
    Тест на добавление новой цены работы через API с проверкой базы данных.
    """
    from app.database.models import WorkPrices

    data = {
        "work": seed_work["work_id"],
        "name": "New Work Price",
        "category": 2,
        "price": 200.00,
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/work_prices/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New work price added successfully"

    # Проверяем, что цена работы добавлена в базу
    work_price = db_session.query(WorkPrices).filter_by(category=2).first()
    assert work_price is not None
    assert str(work_price.work_price_id) == response.json["work_price_id"]
    assert str(work_price.work) == seed_work["work_id"]
    assert work_price.category == 2
    assert work_price.price == 200.00


def test_view_work_price(client, jwt_token, seed_work_price, seed_work):
    """
    Тест на просмотр данных цены работы через API с проверкой вложенности.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/work_prices/{str(seed_work_price['work_price_id'])}/view", headers=headers
    )

    assert response.status_code == 200
    assert "work_price" in response.json
    assert response.json["msg"] == "Work price found successfully"

    # Проверяем данные из ответа
    work_price_data = response.json["work_price"]
    assert work_price_data["work_price_id"] == str(seed_work_price["work_price_id"])

    assert work_price_data["work"] == str(seed_work["work_id"])


def test_soft_delete_work_price(client, jwt_token, seed_work_price, db_session):
    """
    Тест на мягкое удаление цены работы.
    """
    from app.database.models import WorkPrices

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/work_prices/{str(seed_work_price['work_price_id'])}/delete/soft",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Work price {seed_work_price['work_price_id']} soft deleted successfully"
    )

    # Проверяем, что цена работы помечена как удаленная в базе
    work_price = (
        db_session.query(WorkPrices)
        .filter_by(work_price_id=seed_work_price["work_price_id"])
        .first()
    )
    assert work_price is not None
    assert work_price.deleted is True


def test_hard_delete_work_price(client, jwt_token, seed_work_price, db_session):
    """
    Тест на жесткое удаление цены работы.
    """
    from app.database.models import WorkPrices

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/work_prices/{str(seed_work_price['work_price_id'])}/delete/hard",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Work price {seed_work_price['work_price_id']} hard deleted successfully"
    )

    # Проверяем, что цена работы удалена из базы
    work_price = (
        db_session.query(WorkPrices)
        .filter_by(work_price_id=seed_work_price["work_price_id"])
        .first()
    )
    assert work_price is None


def test_edit_work_price(client, jwt_token, seed_work_price, db_session):
    """
    Тест на редактирование данных цены работы через API.
    """
    from app.database.models import WorkPrices

    data = {"name": "Updated Work Price", "price": 300.00}
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/work_prices/{str(seed_work_price['work_price_id'])}/edit",
        json=data,
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Work price edited successfully"

    # Проверяем обновленные данные в базе
    work_price = (
        db_session.query(WorkPrices)
        .filter_by(work_price_id=seed_work_price["work_price_id"])
        .first()
    )
    assert work_price is not None
    assert work_price.price == 300.00


def test_get_all_work_prices(client, jwt_token, seed_work_price):
    """
    Тест на получение списка цен работы через API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/work_prices/all", headers=headers)

    assert response.status_code == 200
    assert "work_prices" in response.json
    assert response.json["msg"] == "Work prices found successfully"

    # Проверяем, что тестовая цена работы присутствует в списке
    work_prices = response.json["work_prices"]
    assert any(
        wp["work_price_id"] == str(seed_work_price["work_price_id"])
        for wp in work_prices
    )
