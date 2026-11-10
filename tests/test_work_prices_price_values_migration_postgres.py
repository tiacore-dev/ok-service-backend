"""Run against TEST_DATABASE_URL; all DDL happens in a throwaway schema and is rolled back."""

import os
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from dotenv import load_dotenv

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic/versions/20261111120000_work_prices_price_values.py"
)

# Includes a legacy value (-5) that the new rule forbids: it must survive as is.
LEGACY_PRICES = [Decimal("100.00"), Decimal("0.00"), Decimal("-1.00"), Decimal("-5.00")]


def _load_migration():
    spec = spec_from_file_location("work_prices_price_values_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _insert(connection, price):
    connection.execute(
        sa.text(
            "INSERT INTO work_prices (work_price_id, work, category, price) "
            "VALUES (:id, :work, 1, :price)"
        ),
        {"id": uuid4(), "work": uuid4(), "price": price},
    )


def _constraint_names(connection):
    return set(
        connection.execute(
            sa.text(
                "SELECT conname FROM pg_constraint c "
                "JOIN pg_namespace n ON n.oid = c.connamespace "
                "WHERE n.nspname = current_schema()"
            )
        ).scalars()
    )


def test_migration_keeps_existing_rows_and_enforces_new_values():
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
                schema = f"test_work_prices_values_{uuid4().hex}"
                connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
                connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
                # Relevant shape of work_prices before revision 20261111120000.
                connection.exec_driver_sql(
                    "CREATE TABLE work_prices ("
                    " work_price_id UUID PRIMARY KEY,"
                    " work UUID,"
                    " category INTEGER NOT NULL,"
                    " price NUMERIC(10, 2) NOT NULL)"
                )
                for price in LEGACY_PRICES:
                    _insert(connection, price)
                before = connection.execute(
                    sa.text("SELECT work_price_id, price FROM work_prices ORDER BY 1")
                ).all()

                with Operations.context(MigrationContext.configure(connection)):
                    migration.upgrade()

                after = connection.execute(
                    sa.text("SELECT work_price_id, price FROM work_prices ORDER BY 1")
                ).all()
                assert after == before
                assert migration.CONSTRAINT_NAME in _constraint_names(connection)

                for allowed in ("-1", "0", "15.50"):
                    _insert(connection, Decimal(allowed))
                for forbidden in ("-2", "-1.50", "-0.01"):
                    with connection.begin_nested() as savepoint:
                        with pytest.raises(sa.exc.IntegrityError):
                            _insert(connection, Decimal(forbidden))
                        savepoint.rollback()

                with Operations.context(MigrationContext.configure(connection)):
                    migration.downgrade()

                assert migration.CONSTRAINT_NAME not in _constraint_names(connection)
                _insert(connection, Decimal("-2"))
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
