import json

from flask_jwt_extended import create_refresh_token


def _login_payload():
    return {"login": "test_admin", "password": "qweasdzcx"}


def test_auth_health_endpoint_is_available(client):
    response = client.get("/auth/health")

    assert response.status_code == 200
    assert response.get_json() == {"msg": "Hello, world!"}


def test_auth_login_endpoint_returns_tokens(client, seed_admin):
    response = client.post("/auth/login", json=_login_payload())

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["msg"] == "Authentication successful"
    assert payload["user_id"] == seed_admin["user_id"]
    assert isinstance(payload["access_token"], str)
    assert isinstance(payload["refresh_token"], str)


def test_auth_login_endpoint_rejects_bad_password(client):
    response = client.post(
        "/auth/login",
        json={"login": "test_admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.get_json()["msg"] == "Bad username or password"


def test_auth_refresh_endpoint_returns_new_tokens(client, test_app, seed_admin):
    identity = {
        "login": seed_admin["login"],
        "role": seed_admin["role"],
        "user_id": seed_admin["user_id"],
    }
    with test_app.app_context():
        refresh_token = create_refresh_token(identity=json.dumps(identity))

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["msg"] == "Token refreshed successfully"
    assert isinstance(payload["access_token"], str)
    assert isinstance(payload["refresh_token"], str)


def test_auth_refresh_endpoint_rejects_missing_token(client):
    response = client.post("/auth/refresh", json={"refresh_token": ""})

    assert response.status_code == 400
    assert response.get_json()["msg"] == "Missing refresh token"
