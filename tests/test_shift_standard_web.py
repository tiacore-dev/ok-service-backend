from uuid import UUID

from app.database.models import ShiftStandards


def test_shift_standard_crud(client, jwt_token_admin, db_session):
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}
    payload = {
        "category": 123456,
        "standard": 8.5,
        "production_rate_rub": 1500.25,
        "penalty_rate_percent": 100,
        "notification_text": "Shift exceeds the standard",
    }

    create = client.post("/shift_standards/add", json=payload, headers=headers)
    assert create.status_code == 200
    item_id = create.json["shift_standard_id"]

    view = client.get(f"/shift_standards/{item_id}/view", headers=headers)
    assert view.status_code == 200
    assert view.json["shift_standard"]["standard"] == payload["standard"]

    assert view.json["shift_standard"]["production_rate_rub"] == 1500.25
    assert view.json["shift_standard"]["penalty_rate_percent"] == 100

    edit = client.patch(
        f"/shift_standards/{item_id}/edit",
        json={"notification_text": None, "standard": 7.5, "production_rate_rub": 0},
        headers=headers,
    )
    assert edit.status_code == 200
    assert (
        db_session.query(ShiftStandards)
        .filter_by(shift_standard_id=UUID(item_id))
        .one()
        .notification_text
        is None
    )

    db_session.expire_all()
    stored = db_session.query(ShiftStandards).filter_by(shift_standard_id=UUID(item_id)).one()
    assert stored.production_rate_rub == 0
    assert stored.penalty_rate_percent == 100
    cleared = client.patch(
        f"/shift_standards/{item_id}/edit",
        json={"production_rate_rub": None, "penalty_rate_percent": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    db_session.expire_all()
    stored = db_session.query(ShiftStandards).filter_by(shift_standard_id=UUID(item_id)).one()
    assert stored.production_rate_rub is None
    assert stored.penalty_rate_percent is None

    listed = client.get("/shift_standards/all", headers=headers)
    assert listed.status_code == 200
    listed_item = next(item for item in listed.json["shift_standards"] if item["shift_standard_id"] == item_id)
    assert listed_item["production_rate_rub"] is None
    assert listed_item["penalty_rate_percent"] is None

    deleted = client.delete(f"/shift_standards/{item_id}/delete/hard", headers=headers)
    assert deleted.status_code == 200


def test_shift_standard_rejects_non_positive_standard(client, jwt_token_admin):
    response = client.post(
        "/shift_standards/add",
        json={"category": 991231, "standard": 0},
        headers={"Authorization": f"Bearer {jwt_token_admin}"},
    )
    assert response.status_code == 400


def test_shift_standard_category_is_unique(client, jwt_token_admin):
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}
    payload = {"category": 991233, "standard": 8}
    first = client.post("/shift_standards/add", json=payload, headers=headers)
    assert first.status_code == 200

    duplicate = client.post("/shift_standards/add", json=payload, headers=headers)
    assert duplicate.status_code == 409

    client.delete(
        f"/shift_standards/{first.json['shift_standard_id']}/delete/hard",
        headers=headers,
    )


def test_shift_standard_mutations_require_admin(client, jwt_token_user):
    response = client.post(
        "/shift_standards/add",
        json={"category": 991232, "standard": 8},
        headers={"Authorization": f"Bearer {jwt_token_user}"},
    )
    assert response.status_code == 403
