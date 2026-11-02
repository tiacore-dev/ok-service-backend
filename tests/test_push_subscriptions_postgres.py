"""Run only with an explicitly supplied disposable PostgreSQL database."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.adapters.push_subscriptions import SQLAlchemyPushSubscriptionRepository
from app.database import db_globals
from app.use_cases.push_subscriptions import RegisterPushSubscription, RevokePushSubscription


@pytest.fixture
def database(monkeypatch):
    url = os.getenv("OK41_TEST_DATABASE_URL")
    if not url:
        pytest.skip("OK41_TEST_DATABASE_URL must point to a disposable PostgreSQL database")
    schema = "push_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url)
    @event.listens_for(engine, "connect")
    def set_schema(conn, _):
        old_autocommit = conn.autocommit
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(f'SET search_path TO "{schema}"')
        cursor.close()
        conn.autocommit = old_autocommit
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (user_id uuid PRIMARY KEY)"))
        path = Path("alembic/versions/20261104120000_push_subscriptions.py")
        spec = spec_from_file_location("push_migration", path)
        assert spec is not None and spec.loader is not None
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        setattr(module, "op", Operations(MigrationContext.configure(connection)))
        module.upgrade()
    monkeypatch.setattr(db_globals, "Session", sessionmaker(bind=engine))
    yield engine, module
    engine.dispose()
    with admin.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


def test_registration_transfer_revocation_constraints_and_migration(database):
    engine, migration = database
    user, other, browser, second = uuid4(), uuid4(), uuid4(), uuid4()
    with engine.begin() as c:
        c.execute(text("INSERT INTO users VALUES (:a), (:b)"), {"a": user, "b": other})
    repo = SQLAlchemyPushSubscriptionRepository()
    register = RegisterPushSubscription(repo)
    first = register.execute(user, browser, "web", "token-1")
    repeat = register.execute(user, browser, "web", "token-2")
    assert repeat.subscription_id == first.subscription_id and repeat.token == "token-2"
    another = register.execute(user, second, "web", "token-3")
    assert another.subscription_id != first.subscription_id
    moved = register.execute(other, browser, "web", "token-2")
    assert RevokePushSubscription(repo).execute(moved.subscription_id, user) is None
    with engine.connect() as connection:
        previous = connection.execute(text("SELECT active, revoked_at FROM push_subscriptions WHERE subscription_id = :id"), {"id": first.subscription_id}).one()
        assert previous.active is False and previous.revoked_at is not None
        assert connection.execute(text("SELECT active FROM push_subscriptions WHERE subscription_id = :id"), {"id": another.subscription_id}).scalar_one() is True
    revoked = RevokePushSubscription(repo).execute(moved.subscription_id, other)
    assert revoked is not None
    assert not revoked.active and revoked.revoked_at is not None
    repeated_revoke = RevokePushSubscription(repo).execute(moved.subscription_id, other)
    assert repeated_revoke is not None and repeated_revoke.revoked_at == revoked.revoked_at
    assert register.execute(other, browser, "web", "token-2").subscription_id == moved.subscription_id
    with pytest.raises(IntegrityError), engine.begin() as c:
        c.execute(text("INSERT INTO push_subscriptions VALUES (:id, :user, :browser, 'web', 'token-2', true, 1, 1, NULL)"), {"id": uuid4(), "user": user, "browser": uuid4()})
    # A token moving to another browser revokes its prior owner atomically.
    transferred = register.execute(user, second, "web", "token-2")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT active FROM push_subscriptions WHERE subscription_id = :id"), {"id": moved.subscription_id}).scalar_one() is False
        assert connection.execute(text("SELECT active FROM push_subscriptions WHERE subscription_id = :id"), {"id": transferred.subscription_id}).scalar_one() is True
    # A failed FK insert must roll back the preceding revocation.
    with pytest.raises(IntegrityError):
        register.execute(uuid4(), second, "web", "new-token")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT active FROM push_subscriptions WHERE subscription_id = :id"), {"id": transferred.subscription_id}).scalar_one() is True
    with engine.begin() as c:
        setattr(migration, "op", Operations(MigrationContext.configure(c)))
        migration.downgrade()
        assert "push_subscriptions" not in inspect(c).get_table_names()
        migration.upgrade()
        assert "push_subscriptions" in inspect(c).get_table_names()


def test_competing_registrations_wait_and_transfer(database):
    engine, _ = database
    user, other, browser = uuid4(), uuid4(), uuid4()
    with engine.begin() as c:
        c.execute(text("INSERT INTO users VALUES (:a), (:b)"), {"a": user, "b": other})
    register = RegisterPushSubscription(SQLAlchemyPushSubscriptionRepository())
    register.execute(user, browser, "web", "old")
    with engine.connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        transaction = blocker.begin()
        pid = blocker.execute(text("select pg_backend_pid()" )).scalar_one()
        blocker.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": "push:browser:" + str(browser)})
        future = pool.submit(register.execute, other, browser, "web", "new")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with engine.connect() as observer:
                waiting = observer.execute(text("SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE :pid = ANY(pg_blocking_pids(pid)))"), {"pid": pid}).scalar_one()
            if waiting:
                break
            time.sleep(0.01)
        else:
            transaction.rollback()
            pytest.fail("registration did not wait on the browser lock")
        transaction.commit()
        result = future.result(timeout=5)
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT user_id, subscription_id FROM push_subscriptions WHERE browser_id = :browser AND active"), {"browser": browser}).all()
        assert len(rows) == 1 and rows[0].user_id == other and rows[0].subscription_id == result.subscription_id
