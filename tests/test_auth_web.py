import json
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from flask_jwt_extended import create_access_token, decode_token

from app.adapters.auth_sessions import SQLAlchemyAuthSessionRepository
from app.database.time_utils import utc_epoch_milliseconds


def _login_payload():
    return {"login": "test_admin", "password": "qweasdzcx"}


def _login(client):
    response = client.post("/auth/login", json=_login_payload())
    assert response.status_code == 200
    return response.get_json()


def _claims(app, token):
    with app.app_context():
        return decode_token(token)


def test_auth_health_endpoint_is_available(client):
    response = client.get("/auth/health")

    assert response.status_code == 200
    assert response.get_json() == {"msg": "Hello, world!"}


def test_auth_login_endpoint_returns_session_bound_tokens(client, test_app, seed_admin):
    payload = _login(client)
    access_claims = _claims(test_app, payload["access_token"])
    refresh_claims = _claims(test_app, payload["refresh_token"])

    assert payload["msg"] == "Authentication successful"
    assert payload["user_id"] == seed_admin["user_id"]
    assert access_claims["session_id"] == refresh_claims["session_id"]
    assert access_claims["jti"] and refresh_claims["jti"]
    assert isinstance(access_claims["iat"], int) and isinstance(
        access_claims["exp"], int
    )
    assert isinstance(refresh_claims["iat"], int) and isinstance(
        refresh_claims["exp"], int
    )

    session = SQLAlchemyAuthSessionRepository().get_session(
        UUID(refresh_claims["session_id"])
    )
    stored = SQLAlchemyAuthSessionRepository().get_refresh_token(
        UUID(refresh_claims["jti"])
    )
    assert session is not None and stored is not None
    assert str(session.current_token_jti) == refresh_claims["jti"]
    assert stored.session_id == session.session_id


def test_auth_login_endpoint_rejects_bad_password(client):
    response = client.post(
        "/auth/login",
        json={"login": "test_admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.get_json()["msg"] == "Bad username or password"


def test_auth_refresh_rotates_tokens_and_rejects_reuse(client, test_app, seed_admin):
    original = _login(client)
    response = client.post(
        "/auth/refresh", json={"refresh_token": original["refresh_token"]}
    )

    assert response.status_code == 200
    refreshed = response.get_json()
    old = _claims(test_app, original["refresh_token"])
    current = _claims(test_app, refreshed["refresh_token"])
    assert current["session_id"] == old["session_id"]
    assert current["jti"] != old["jti"]
    assert (
        _claims(test_app, refreshed["access_token"])["session_id"] == old["session_id"]
    )

    reuse = client.post(
        "/auth/refresh", json={"refresh_token": original["refresh_token"]}
    )
    assert reuse.status_code == 401
    session = SQLAlchemyAuthSessionRepository().get_session(UUID(old["session_id"]))
    assert session is not None and session.revoked_at is not None


def test_concurrent_refresh_allows_at_most_one_success(test_app, seed_admin):
    with test_app.test_client() as client:
        original = _login(client)

    def refresh_once():
        with test_app.test_client() as client:
            return client.post(
                "/auth/refresh", json={"refresh_token": original["refresh_token"]}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _ignored: refresh_once(), range(2)))
    assert statuses.count(200) <= 1
    assert statuses.count(401) >= 1


def test_access_with_revoked_session_and_without_session_id_is_rejected(
    client, test_app, seed_admin
):
    payload = _login(client)
    claims = _claims(test_app, payload["access_token"])
    session_id = UUID(claims["session_id"])
    assert SQLAlchemyAuthSessionRepository().revoke_session(
        session_id, utc_epoch_milliseconds()
    )

    revoked = client.get(
        "/users/all", headers={"Authorization": f"Bearer {payload['access_token']}"}
    )
    assert revoked.status_code == 401

    with test_app.app_context():
        legacy = create_access_token(
            identity=json.dumps({"user_id": seed_admin["user_id"], "role": "admin"})
        )
    missing = client.get("/users/all", headers={"Authorization": f"Bearer {legacy}"})
    assert missing.status_code == 401


def test_deleted_user_is_rejected_and_database_errors_are_unavailable(
    client, test_app, db_session, seed_admin, monkeypatch
):
    from app.database.models import Users

    payload = _login(client)
    user = db_session.get(Users, UUID(seed_admin["user_id"]))
    assert user is not None
    user.deleted = True
    db_session.commit()
    try:
        deleted = client.get(
            "/users/all", headers={"Authorization": f"Bearer {payload['access_token']}"}
        )
        assert deleted.status_code == 401
    finally:
        user.deleted = False
        db_session.commit()

    from app.web.auth import jwt_callbacks

    monkeypatch.setattr(
        jwt_callbacks.SQLAlchemyAuthSessionRepository,
        "is_session_active",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("database unavailable")
        ),
    )
    unavailable = client.get(
        "/users/all", headers={"Authorization": f"Bearer {payload['access_token']}"}
    )
    assert unavailable.status_code == 503
    assert unavailable.get_json() == {"msg": "Authentication unavailable"}


def test_active_user_lookup_database_error_is_unavailable(
    client, seed_admin, monkeypatch
):
    payload = _login(client)
    from app.web.auth import jwt_callbacks

    monkeypatch.setattr(
        jwt_callbacks,
        "_active_user",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("database unavailable")
        ),
    )

    unavailable = client.get(
        "/users/all", headers={"Authorization": f"Bearer {payload['access_token']}"}
    )
    assert unavailable.status_code == 503
    assert unavailable.get_json() == {"msg": "Authentication unavailable"}


def test_refresh_rotation_database_error_is_unavailable(
    client, seed_admin, monkeypatch
):
    payload = _login(client)

    monkeypatch.setattr(
        SQLAlchemyAuthSessionRepository,
        "rotate_refresh_token",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("database unavailable")
        ),
    )

    unavailable = client.post(
        "/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    )
    assert unavailable.status_code == 503
    assert unavailable.get_json() == {"msg": "Authentication unavailable"}


def test_auth_logs_never_include_tokens(client, caplog, seed_admin):
    payload = _login(client)
    response = client.post(
        "/auth/refresh", json={"refresh_token": payload["refresh_token"]}
    )

    assert response.status_code == 200
    text = caplog.text
    assert payload["access_token"] not in text
    assert payload["refresh_token"] not in text
    assert response.get_json()["access_token"] not in text
    assert response.get_json()["refresh_token"] not in text


def test_auth_refresh_endpoint_rejects_missing_token(client):
    response = client.post("/auth/refresh", json={"refresh_token": ""})

    assert response.status_code == 400
    assert response.get_json()["msg"] == "Missing refresh token"
