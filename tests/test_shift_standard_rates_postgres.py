"""Run with --noconftest against TEST_DATABASE_URL; all DDL is rolled back."""
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from dotenv import load_dotenv


def test_shift_rate_migration_preserves_old_records_and_enforces_ranges():
    load_dotenv(Path(__file__).parents[1] / ".env")
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required")
    path = Path(__file__).parents[1] / "alembic/versions/20261021120000_shift_standard_rates.py"
    spec = spec_from_file_location("shift_rates_postgres_migration", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine(url)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                schema = f"test_shift_rates_{uuid4().hex}"
                connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
                connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
                connection.exec_driver_sql("CREATE TABLE shift_standards (category INTEGER PRIMARY KEY, standard FLOAT NOT NULL)")
                connection.exec_driver_sql("INSERT INTO shift_standards VALUES (1, 8.5)")
                with Operations.context(MigrationContext.configure(connection)):
                    migration.upgrade()
                assert connection.exec_driver_sql("SELECT * FROM shift_standards").one() == (1, 8.5, None, None)
                for production, penalty in [(0, 0), (1500.25, 100), (sys.float_info.max, 100), (None, None)]:
                    connection.execute(sa.text(
                        "UPDATE shift_standards SET production_rate_rub=:production, penalty_rate_percent=:penalty"
                    ), {"production": production, "penalty": penalty})
                for field, value in [
                    ("production_rate_rub", -0.01),
                    ("production_rate_rub", float("nan")),
                    ("production_rate_rub", float("inf")),
                    ("production_rate_rub", float("-inf")),
                    ("penalty_rate_percent", -0.01),
                    ("penalty_rate_percent", 100.01),
                ]:
                    with connection.begin_nested() as savepoint:
                        with pytest.raises(sa.exc.IntegrityError):
                            connection.execute(sa.text(f"UPDATE shift_standards SET {field}=:value"), {"value": value})
                        savepoint.rollback()
                with Operations.context(MigrationContext.configure(connection)):
                    migration.downgrade()
                assert connection.exec_driver_sql("SELECT * FROM shift_standards").one() == (1, 8.5)
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
