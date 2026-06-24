import json

from sqlalchemy import text

from app.web.subscriptions import routes as subscription_routes


def _auth_headers(jwt_token):
    return {"Authorization": f"Bearer {jwt_token}"}


def test_subscribe_creates_and_updates_subscription(client, jwt_token, db_session):
    headers = _auth_headers(jwt_token)
    payload = {
        "endpoint": "https://push.example/one",
        "keys": {"p256dh": "key-1", "auth": "auth-1"},
    }

    create_response = client.post("/subscriptions/subscribe", headers=headers, json=payload)
    assert create_response.status_code == 201
    created = create_response.get_json()
    assert created["msg"] == "Subscription added."
    assert isinstance(created["subscription_id"], str)

    update_response = client.post("/subscriptions/subscribe", headers=headers, json=payload)
    assert update_response.status_code == 200
    updated = update_response.get_json()
    assert updated["msg"] == "Subscription already exists."
    assert updated["subscription_id"] == created["subscription_id"]

    stored = db_session.execute(
        text(
            "SELECT endpoint, keys FROM subscriptions WHERE subscription_id = :subscription_id"
        ),
        {"subscription_id": created["subscription_id"]},
    ).fetchone()
    assert stored[0] == payload["endpoint"]
    assert json.loads(stored[1]) == payload["keys"]


def test_subscriptions_all_and_unsubscribe_work(client, jwt_token):
    headers = _auth_headers(jwt_token)
    payload = {
        "endpoint": "https://push.example/two",
        "keys": {"p256dh": "key-2", "auth": "auth-2"},
    }

    create_response = client.post("/subscriptions/subscribe", headers=headers, json=payload)
    subscription_id = create_response.get_json()["subscription_id"]

    all_response = client.get("/subscriptions/all", headers=headers)
    assert all_response.status_code == 200
    subscriptions = all_response.get_json()["subscriptions"]
    assert any(item["subscription_id"] == subscription_id for item in subscriptions)

    unsubscribe_response = client.delete(
        f"/subscriptions/{subscription_id}/unsubscribe", headers=headers
    )
    assert unsubscribe_response.status_code == 200
    assert unsubscribe_response.get_json()["msg"] == "Subscription removed successfully."


def test_send_notification_uses_webpush_and_handles_invalid_subscription_id(
    client, jwt_token, monkeypatch
):
    headers = _auth_headers(jwt_token)
    payload = {
        "endpoint": "https://push.example/three",
        "keys": {"p256dh": "key-3", "auth": "auth-3"},
    }

    create_response = client.post("/subscriptions/subscribe", headers=headers, json=payload)
    subscription_id = create_response.get_json()["subscription_id"]

    monkeypatch.setattr(subscription_routes, "_vapid_private_key", lambda: "private-key")

    seen = {}

    def fake_webpush(**kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(subscription_routes, "webpush", fake_webpush)

    response = client.post(
        "/subscriptions/send_notification",
        headers=headers,
        json={"subscription_id": subscription_id, "message": "Hello"},
    )
    assert response.status_code == 200
    assert response.get_json()["msg"] == "Notification sent successfully."
    assert seen["subscription_info"]["endpoint"] == payload["endpoint"]
    assert json.loads(seen["data"]) == {"header": "Test Notification", "text": "Hello"}

    missing_response = client.post(
        "/subscriptions/send_notification",
        headers=headers,
        json={"subscription_id": "not-a-uuid", "message": "Hello"},
    )
    assert missing_response.status_code == 400
    assert missing_response.get_json()["msg"] == "Invalid subscription ID format."
