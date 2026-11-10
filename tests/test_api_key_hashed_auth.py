from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa

from app.database.models import ApiKeys, KeyPermissionTypeRelations, PermissionTypes
from app.database.time_utils import utc_epoch_milliseconds
from app.domain.api_keys import hash_api_key

PROTECTED_ROUTE = "/roles/all"

MIGRATION_PATH = (
    Path(__file__).parents[1] / "alembic/versions/20261108120000_hash_api_keys.py"
)


def _migration_hash_sql() -> str:
    spec = spec_from_file_location("hash_api_keys_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration.HASH_SQL


def _admin_headers(jwt_token_admin):
    return {"Authorization": f"Bearer {jwt_token_admin}"}


def _roles_permission(db_session):
    permission = (
        db_session.query(PermissionTypes).filter_by(code="roles-list").one_or_none()
    )
    if permission is None:
        permission = PermissionTypes(code="roles-list", description="GET /roles/all")
        db_session.add(permission)
        db_session.flush()
    return permission


def _grant(db_session, api_key_id):
    permission = _roles_permission(db_session)
    db_session.add(
        KeyPermissionTypeRelations(
            api_key_id=api_key_id, permission_type_id=permission.permission_type_id
        )
    )
    db_session.commit()


def _generate(client, jwt_token_admin, expires_at=1_893_456_000_000):
    name = f"hashed-{uuid4().hex[:12]}"
    response = client.post(
        "/api-key/generate",
        headers=_admin_headers(jwt_token_admin),
        json={"name": name, "expires_at": expires_at},
    )
    assert response.status_code == 200
    body = response.get_json()
    return name, body["api_key_id"], body["token"]


def test_generated_key_is_stored_only_as_hash(client, jwt_token_admin, db_session):
    name, _, raw_key = _generate(client, jwt_token_admin)

    row = (
        db_session.execute(
            sa.text("SELECT * FROM api_keys WHERE name = :name"), {"name": name}
        )
        .mappings()
        .one()
    )
    columns = set(row.keys())
    assert "token" not in columns
    assert row["api_key_hashed"] == hash_api_key(raw_key)
    assert all(raw_key not in str(value) for value in row.values())


def test_plaintext_and_hash_are_not_retrievable_after_creation(
    client, jwt_token_admin
):
    _, api_key_id, raw_key = _generate(client, jwt_token_admin)
    headers = _admin_headers(jwt_token_admin)

    view = client.get(f"/api-key/{api_key_id}/view", headers=headers)
    listing = client.get("/api-key/all", headers=headers)

    for response in (view, listing):
        assert response.status_code == 200
        text = response.get_data(as_text=True)
        assert raw_key not in text
        assert hash_api_key(raw_key) not in text
        assert "api_key_hashed" not in text
    assert "token" not in view.get_json()["api_key"]


def test_generated_key_authenticates_with_permission(
    client, jwt_token_admin, db_session
):
    _, api_key_id, raw_key = _generate(client, jwt_token_admin)

    assert client.get(PROTECTED_ROUTE, headers={"API-Key": raw_key}).status_code == 403
    _grant(db_session, api_key_id)
    assert client.get(PROTECTED_ROUTE, headers={"API-Key": raw_key}).status_code == 200


def test_key_hashed_by_migration_sql_keeps_working(client, db_session):
    """A legacy plaintext key hashed by the migration SQL authenticates as before."""
    legacy_raw_key = f"legacy-{uuid4()}"
    api_key_id = uuid4()
    hash_sql = _migration_hash_sql().replace("token", ":legacy_raw_key")
    db_session.execute(
        sa.text(
            "INSERT INTO api_keys (api_key_id, name, api_key_hashed) "
            f"VALUES (:api_key_id, :name, {hash_sql})"
        ),
        {
            "api_key_id": api_key_id,
            "name": f"legacy-{uuid4().hex[:12]}",
            "legacy_raw_key": legacy_raw_key,
        },
    )
    db_session.commit()
    _grant(db_session, api_key_id)

    response = client.get(PROTECTED_ROUTE, headers={"API-Key": legacy_raw_key})

    assert response.status_code == 200


def test_invalid_key_and_hash_as_key_are_rejected(
    client, jwt_token_admin, db_session
):
    _, api_key_id, raw_key = _generate(client, jwt_token_admin)
    _grant(db_session, api_key_id)

    for candidate in ("invalid", raw_key + "x", hash_api_key(raw_key)):
        response = client.get(PROTECTED_ROUTE, headers={"API-Key": candidate})
        assert response.status_code == 403
        assert response.get_json() == {"msg": "Invalid API key"}


def test_revoked_key_is_rejected(client, jwt_token_admin, db_session):
    _, api_key_id, raw_key = _generate(client, jwt_token_admin)
    _grant(db_session, api_key_id)
    assert client.get(PROTECTED_ROUTE, headers={"API-Key": raw_key}).status_code == 200

    deleted = client.delete(
        f"/api-key/{api_key_id}/delete", headers=_admin_headers(jwt_token_admin)
    )
    assert deleted.status_code == 200

    response = client.get(PROTECTED_ROUTE, headers={"API-Key": raw_key})
    assert response.status_code == 403
    assert response.get_json() == {"msg": "Invalid API key"}


def test_expired_key_is_rejected(client, db_session):
    raw_key = f"expired-{uuid4()}"
    key = ApiKeys(
        name=f"expired-{uuid4().hex[:12]}",
        api_key_hashed=hash_api_key(raw_key),
        expires_at=utc_epoch_milliseconds() - 1,
    )
    db_session.add(key)
    db_session.flush()
    _grant(db_session, key.api_key_id)

    response = client.get(PROTECTED_ROUTE, headers={"API-Key": raw_key})

    assert response.status_code == 403
    assert response.get_json() == {"msg": "API key expired"}
