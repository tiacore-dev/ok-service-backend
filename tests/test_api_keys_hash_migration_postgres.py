"""Run against TEST_DATABASE_URL; all DDL happens in a throwaway schema and is rolled back."""
import os
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from dotenv import load_dotenv

from app.domain.api_keys import generate_raw_api_key, hash_api_key

MIGRATION_PATH = (
    Path(__file__).parents[1] / "alembic/versions/20261108120000_hash_api_keys.py"
)

LEGACY_KEYS = [
    generate_raw_api_key(),
    str(uuid4()),
    "legacy-ключ-🔑",
]


def _load_migration():
    spec = spec_from_file_location("hash_api_keys_postgres_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _columns(connection):
    return {
        row[0]
        for row in connection.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = 'api_keys'"
            )
        )
    }


def test_migration_hashes_existing_keys_and_drops_plaintext():
    load_dotenv(Path(__file__).parents[1] / ".env")
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required")
    migration = _load_migration()
    engine = sa.create_engine(url)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                schema = f"test_api_keys_hash_{uuid4().hex}"
                connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
                connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
                # Legacy shape of api_keys before revision 20261108120000.
                connection.exec_driver_sql(
                    "CREATE TABLE api_keys ("
                    " api_key_id UUID PRIMARY KEY,"
                    " name VARCHAR NOT NULL,"
                    " token VARCHAR NOT NULL,"
                    " expires_at BIGINT,"
                    " CONSTRAINT uq_api_keys_name UNIQUE (name),"
                    " CONSTRAINT uq_api_keys_token UNIQUE (token))"
                )
                ids = {}
                for index, raw_key in enumerate(LEGACY_KEYS):
                    ids[raw_key] = uuid4()
                    connection.execute(
                        sa.text(
                            "INSERT INTO api_keys (api_key_id, name, token, expires_at) "
                            "VALUES (:id, :name, :token, :expires_at)"
                        ),
                        {
                            "id": ids[raw_key],
                            "name": f"legacy-{index}",
                            "token": raw_key,
                            "expires_at": 1_893_456_000_000 if index else None,
                        },
                    )

                with Operations.context(MigrationContext.configure(connection)):
                    migration.upgrade()

                assert "token" not in _columns(connection)
                assert "api_key_hashed" in _columns(connection)
                rows = connection.execute(
                    sa.text("SELECT * FROM api_keys")
                ).mappings().all()
                assert len(rows) == len(LEGACY_KEYS)
                for raw_key in LEGACY_KEYS:
                    # Lookup used by the auth decorator finds every legacy key.
                    found = connection.execute(
                        sa.text(
                            "SELECT api_key_id FROM api_keys "
                            "WHERE api_key_hashed = :digest"
                        ),
                        {"digest": hash_api_key(raw_key)},
                    ).scalar_one()
                    assert found == ids[raw_key]
                    for row in rows:
                        assert all(raw_key not in str(value) for value in row.values())

                with connection.begin_nested() as savepoint:
                    with pytest.raises(sa.exc.IntegrityError):
                        connection.execute(
                            sa.text(
                                "INSERT INTO api_keys (api_key_id, name, api_key_hashed) "
                                "VALUES (:id, 'dup', :digest)"
                            ),
                            {"id": uuid4(), "digest": hash_api_key(LEGACY_KEYS[0])},
                        )
                    savepoint.rollback()
                with connection.begin_nested() as savepoint:
                    with pytest.raises(sa.exc.IntegrityError):
                        connection.execute(
                            sa.text(
                                "INSERT INTO api_keys (api_key_id, name) "
                                "VALUES (:id, 'no-hash')"
                            ),
                            {"id": uuid4()},
                        )
                    savepoint.rollback()

                with (
                    pytest.raises(RuntimeError, match="irreversible"),
                    Operations.context(MigrationContext.configure(connection)),
                ):
                    migration.downgrade()
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def test_migration_hash_sql_does_not_embed_plaintext_values():
    source = MIGRATION_PATH.read_text()
    migration = _load_migration()

    assert migration.down_revision == "20261107120000"
    assert "SELECT" not in migration.HASH_SQL.upper()
    assert "print(" not in source and "logger" not in source
