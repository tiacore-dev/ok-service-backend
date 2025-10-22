from uuid import UUID, uuid4

import pytest


@pytest.fixture
def city_manager(db_session):
    from app.database.managers.cities_manager import CitiesManager

    return CitiesManager(session=db_session)  # type: ignore


def test_add_city(client, jwt_token, db_session):
    """
    Проверяет добавление нового города.
    """
    from app.database.models import Cities

    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {"name": f"City-{uuid4().hex[:6]}"}

    response = client.post("/cities/add", json=payload, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New city added successfully"
    city_id = response.json["city_id"]

    city = db_session.query(Cities).filter_by(city_id=UUID(city_id)).first()
    assert city is not None
    assert city.name == payload["name"]


def test_view_city(client, jwt_token, seed_city):
    """
    Проверяет просмотр информации о городе.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(f"/cities/{seed_city['city_id']}/view", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "City found successfully"
    assert response.json["city"]["city_id"] == seed_city["city_id"]
    assert response.json["city"]["name"] == seed_city["name"]


def test_edit_city(client, jwt_token, seed_city, db_session):
    """
    Проверяет редактирование города.
    """
    from app.database.models import Cities

    headers = {"Authorization": f"Bearer {jwt_token}"}
    new_name = f"Updated-{uuid4().hex[:6]}"
    response = client.patch(
        f"/cities/{seed_city['city_id']}/edit",
        json={"name": new_name},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["msg"] == "City edited successfully"

    city = (
        db_session.query(Cities).filter_by(city_id=UUID(seed_city["city_id"])).first()
    )
    assert city is not None
    assert city.name == new_name


def test_soft_delete_city(client, jwt_token, seed_city, city_manager):
    """
    Проверяет мягкое удаление города.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/cities/{seed_city['city_id']}/delete/soft", headers=headers
    )

    assert response.status_code == 200
    assert (
        response.json["msg"] == f"City {seed_city['city_id']} soft deleted successfully"
    )

    with city_manager.session_scope() as session:
        city = (
            session.query(city_manager.model)
            .filter_by(city_id=seed_city["city_id"])
            .first()
        )
        assert city is not None
        assert city.deleted is True


def test_hard_delete_city(client, jwt_token, seed_city, db_session):
    """
    Проверяет жесткое удаление города.
    """
    from app.database.models import Cities

    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/cities/{seed_city['city_id']}/delete/hard", headers=headers
    )

    assert response.status_code == 200
    assert (
        response.json["msg"] == f"City {seed_city['city_id']} hard deleted successfully"
    )

    city = (
        db_session.query(Cities).filter_by(city_id=UUID(seed_city["city_id"])).first()
    )
    assert city is None


def test_get_all_cities(client, jwt_token, seed_city):
    """
    Проверяет получение списка городов.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get("/cities/all", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Cities found successfully"
    assert "cities" in response.json

    cities = response.json["cities"]
    assert any(city["city_id"] == seed_city["city_id"] for city in cities)
