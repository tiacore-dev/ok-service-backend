from uuid import UUID, uuid4


def _seed_position(db_session, seed_admin, name="Fixture Position"):
    from app.database.models import Positions

    position = Positions(
        position_id=uuid4(),
        name=name,
        created_by=UUID(seed_admin["user_id"]),
    )
    db_session.add(position)
    db_session.commit()
    return position.to_dict()


def test_add_position(client, jwt_token_admin, seed_admin, db_session):
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}
    payload = {"name": f"Position-{uuid4().hex[:6]}"}

    response = client.post("/positions/add", json=payload, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New position added successfully"
    position_id = response.json["position_id"]

    from app.database.models import Positions

    position = (
        db_session.query(Positions)
        .filter_by(position_id=UUID(position_id))
        .first()
    )
    assert position is not None
    assert position.name == payload["name"]


def test_view_position(client, jwt_token, seed_admin, db_session):
    position = _seed_position(db_session, seed_admin)
    headers = {"Authorization": f"Bearer {jwt_token}"}

    response = client.get(f"/positions/{position['position_id']}/view", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Position found successfully"
    assert response.json["position"]["position_id"] == position["position_id"]
    assert response.json["position"]["name"] == position["name"]


def test_edit_position(client, jwt_token_admin, seed_admin, db_session):
    position = _seed_position(db_session, seed_admin)
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}
    new_name = f"Updated-{uuid4().hex[:6]}"

    response = client.patch(
        f"/positions/{position['position_id']}/edit",
        json={"name": new_name},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json["msg"] == "Position updated successfully"

    from app.database.models import Positions

    updated = (
        db_session.query(Positions)
        .filter_by(position_id=UUID(position["position_id"]))
        .first()
    )
    assert updated is not None
    assert updated.name == new_name


def test_delete_position(client, jwt_token_admin, seed_admin, db_session):
    position = _seed_position(db_session, seed_admin)
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}

    response = client.delete(
        f"/positions/{position['position_id']}/delete/hard",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json["msg"]
        == f"Position {position['position_id']} hard deleted successfully"
    )

    from app.database.models import Positions

    deleted = (
        db_session.query(Positions)
        .filter_by(position_id=UUID(position["position_id"]))
        .first()
    )
    assert deleted is None


def test_get_all_positions(client, jwt_token, seed_admin, db_session):
    position = _seed_position(db_session, seed_admin)
    headers = {"Authorization": f"Bearer {jwt_token}"}

    response = client.get("/positions/all", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Positions found successfully"
    assert "positions" in response.json
    assert any(item["position_id"] == position["position_id"] for item in response.json["positions"])
