"""PostgreSQL checks for server-side auth sessions.

Run only with OK41_TEST_DATABASE_URL pointing to a disposable PostgreSQL
database. Each test receives an isolated schema and never touches dev/stage/prod.
"""

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
from sqlalchemy.orm import scoped_session, sessionmaker

from app.adapters.auth_sessions.sqlalchemy_repository import (
    INACTIVE,
    REUSED,
    ROTATED,
    SQLAlchemyAuthSessionRepository,
)
from app.adapters.push_subscriptions import SQLAlchemyPushSubscriptionRepository
from app.database import db_globals
from app.domain.auth_sessions import AuthSession, RefreshToken
from app.use_cases.push_subscriptions import RegisterPushSubscription


@pytest.fixture
def database(monkeypatch):
    url = os.getenv("OK41_TEST_DATABASE_URL")
    if not url:
        pytest.skip("OK41_TEST_DATABASE_URL must point to a disposable PostgreSQL database")

    schema = "auth_sessions_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def set_schema(connection, _):
        old_autocommit = connection.autocommit
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute(f'SET search_path TO "{schema}"')
        cursor.close()
        connection.autocommit = old_autocommit

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (user_id uuid PRIMARY KEY)"))
        migrations = []
        for revision in (
            "20261104120000_push_subscriptions.py",
            "20261105120000_auth_sessions.py",
            "20261106120000_bind_push_subscriptions_to_auth_sessions.py",
        ):
            path = Path("alembic/versions") / revision
            spec = spec_from_file_location(revision, path)
            assert spec is not None and spec.loader is not None
            migration = module_from_spec(spec)
            spec.loader.exec_module(migration)
            setattr(migration, "op", Operations(MigrationContext.configure(connection)))
            migration.upgrade()
            migrations.append(migration)

    monkeypatch.setattr(db_globals, "Session", scoped_session(sessionmaker(bind=engine)))
    yield engine, migrations
    engine.dispose()
    with admin.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


def _session_and_token(user_id, *, now=1_700_000_000_000, browser_id=None):
    session_id, jti = uuid4(), uuid4()
    session = AuthSession(
        session_id, user_id, now, now + 86_400_000, jti, browser_id=browser_id
    )
    token = RefreshToken(jti, session_id, now, now + 86_400_000)
    return session, token


def test_create_revoke_and_migrate_auth_session_records(database):
    engine, migrations = database
    user_id = uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (user_id) VALUES (:user_id)"), {"user_id": user_id})

    repository = SQLAlchemyAuthSessionRepository()
    session, token = _session_and_token(user_id)
    assert repository.create_session_with_refresh_token(session, token) == session
    assert repository.get_refresh_token(token.jti) == token
    assert repository.is_session_active(session.session_id, user_id, session.created_at)

    second = RefreshToken(uuid4(), session.session_id, token.created_at, token.expires_at)
    repository.save_refresh_token(second)
    assert repository.revoke_session(
        session.session_id, user_id, session.created_at + 1
    )
    assert not repository.is_session_active(session.session_id, user_id, session.created_at + 1)
    revoked_session = repository.get_session(session.session_id)
    revoked_first_token = repository.get_refresh_token(token.jti)
    revoked_second_token = repository.get_refresh_token(second.jti)
    assert revoked_session is not None
    assert revoked_first_token is not None
    assert revoked_second_token is not None
    assert revoked_session.revoked_at == session.created_at + 1
    assert revoked_first_token.revoked_at == session.created_at + 1
    assert revoked_second_token.revoked_at == session.created_at + 1

    with engine.begin() as connection:
        migration = migrations[-1]
        setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.downgrade()
        assert "browser_id" not in {item["name"] for item in inspect(connection).get_columns("auth_sessions")}
        migration.upgrade()
        assert "auth_sessions" in inspect(connection).get_table_names()
        assert "refresh_tokens" in inspect(connection).get_table_names()


def test_refresh_jti_is_unique(database):
    engine, _ = database
    user_id = uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (user_id) VALUES (:user_id)"), {"user_id": user_id})
    repository = SQLAlchemyAuthSessionRepository()
    session, token = _session_and_token(user_id)
    repository.create_session_with_refresh_token(session, token)

    other_session = AuthSession(uuid4(), user_id, token.created_at, token.expires_at, token.jti)
    with pytest.raises(IntegrityError):
        repository.create_session(other_session)


def test_competing_refresh_replacements_lock_session_and_only_one_succeeds(database):
    engine, _ = database
    user_id = uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (user_id) VALUES (:user_id)"), {"user_id": user_id})
    repository = SQLAlchemyAuthSessionRepository()
    session, old_token = _session_and_token(user_id)
    repository.create_session_with_refresh_token(session, old_token)
    replacements = [
        RefreshToken(uuid4(), session.session_id, old_token.created_at + 1, old_token.expires_at)
        for _ in range(2)
    ]

    with engine.connect() as blocker, ThreadPoolExecutor(max_workers=2) as pool:
        transaction = blocker.begin()
        blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        blocker.execute(
            text("SELECT 1 FROM auth_sessions WHERE session_id = :session_id FOR UPDATE"),
            {"session_id": session.session_id},
        )
        futures = [
            pool.submit(
                repository.replace_current_refresh_token,
                session.session_id,
                old_token.jti,
                replacement,
                old_token.created_at + 1,
            )
            for replacement in replacements
        ]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with engine.connect() as observer:
                waiting = observer.execute(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                        "WHERE :blocker_pid = ANY(pg_blocking_pids(pid)))"
                    ),
                    {"blocker_pid": blocker_pid},
                ).scalar_one()
            if waiting:
                break
            time.sleep(0.01)
        else:
            transaction.rollback()
            pytest.fail("refresh replacement did not wait for the session row lock")
        transaction.commit()
        results = [future.result(timeout=5) for future in futures]

    assert sorted(results) == [False, True]
    refreshed = repository.get_session(session.session_id)
    assert refreshed is not None
    assert refreshed.current_token_jti in {item.jti for item in replacements}
    consumed = repository.get_refresh_token(old_token.jti)
    assert consumed is not None
    assert consumed.used_at == old_token.created_at + 1
    assert consumed.replaced_by_jti == refreshed.current_token_jti


def test_reused_refresh_revokes_the_whole_session_before_return(database):
    engine, _ = database
    user_id, browser_id = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (user_id) VALUES (:user_id)"), {"user_id": user_id})
    repository = SQLAlchemyAuthSessionRepository()
    session, old_token = _session_and_token(user_id, browser_id=browser_id)
    repository.create_session_with_refresh_token(session, old_token)
    subscription = RegisterPushSubscription(
        SQLAlchemyPushSubscriptionRepository()
    ).execute(user_id, browser_id, session.session_id, "web", "reuse-token")
    replacement = RefreshToken(
        uuid4(), session.session_id, old_token.created_at + 1, old_token.expires_at
    )

    assert repository.rotate_refresh_token(
        session.session_id, old_token.jti, replacement, old_token.created_at + 1
    ) == ROTATED
    assert repository.rotate_refresh_token(
        session.session_id, old_token.jti, RefreshToken(
            uuid4(), session.session_id, old_token.created_at + 2, old_token.expires_at
        ), old_token.created_at + 2
    ) == REUSED

    revoked = repository.get_session(session.session_id)
    old_record = repository.get_refresh_token(old_token.jti)
    new_record = repository.get_refresh_token(replacement.jti)
    assert revoked is not None and revoked.revoked_at == old_token.created_at + 2
    assert old_record is not None and old_record.revoked_at == old_token.created_at + 2
    assert new_record is not None and new_record.revoked_at == old_token.created_at + 2
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT active FROM push_subscriptions WHERE subscription_id = :id"),
            {"id": subscription.subscription_id},
        ).scalar_one() is False


def test_refresh_rotation_extends_session_expiration(database):
    engine, _ = database
    user_id = uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (user_id) VALUES (:user_id)"), {"user_id": user_id})

    repository = SQLAlchemyAuthSessionRepository()
    session, old_token = _session_and_token(user_id)
    repository.create_session_with_refresh_token(session, old_token)
    replacement = RefreshToken(
        uuid4(),
        session.session_id,
        old_token.created_at + 1,
        old_token.expires_at + 86_400_000,
    )

    assert repository.rotate_refresh_token(
        session.session_id, old_token.jti, replacement, old_token.created_at + 1
    ) == ROTATED

    refreshed = repository.get_session(session.session_id)
    assert refreshed is not None
    assert refreshed.expires_at == replacement.expires_at


def test_concurrent_logins_leave_one_active_session_per_browser(database):
    engine, _ = database
    user_id, browser_id = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (user_id) VALUES (:user_id)"), {"user_id": user_id})

    repository = SQLAlchemyAuthSessionRepository()
    first, first_token = _session_and_token(user_id, now=1, browser_id=browser_id)
    second, second_token = _session_and_token(user_id, now=2, browser_id=browser_id)

    with engine.connect() as blocker, ThreadPoolExecutor(max_workers=2) as pool:
        transaction = blocker.begin()
        blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        blocker.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": "auth:browser:" + str(browser_id)},
        )
        first_login = pool.submit(
            repository.create_session_with_refresh_token, first, first_token
        )
        second_login = pool.submit(
            repository.create_session_with_refresh_token, second, second_token
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with engine.connect() as observer:
                waiting = observer.execute(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                        "WHERE :blocker_pid = ANY(pg_blocking_pids(pid)))"
                    ),
                    {"blocker_pid": blocker_pid},
                ).scalar_one()
            if waiting:
                break
            time.sleep(0.01)
        else:
            transaction.rollback()
            pytest.fail("login did not wait for the browser login lock")
        transaction.commit()
        assert first_login.result(timeout=5) == first
        assert second_login.result(timeout=5) == second

    with engine.connect() as connection:
        active_sessions = connection.execute(
            text(
                "SELECT session_id FROM auth_sessions "
                "WHERE browser_id = :browser_id AND revoked_at IS NULL"
            ),
            {"browser_id": browser_id},
        ).scalars().all()
        active_refresh_tokens = connection.execute(
            text(
                "SELECT count(*) FROM refresh_tokens "
                "WHERE session_id IN (:first, :second) AND revoked_at IS NULL"
            ),
            {"first": first.session_id, "second": second.session_id},
        ).scalar_one()
    assert len(active_sessions) == 1
    assert active_refresh_tokens == 1


def test_logout_and_refresh_serialize_and_revoke_bound_subscription(database):
    engine, _ = database
    user_id, browser_id = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (user_id) VALUES (:user_id)"), {"user_id": user_id})
    repository = SQLAlchemyAuthSessionRepository()
    session, token = _session_and_token(user_id, browser_id=browser_id)
    repository.create_session_with_refresh_token(session, token)
    subscription = RegisterPushSubscription(
        SQLAlchemyPushSubscriptionRepository()
    ).execute(user_id, browser_id, session.session_id, "web", "token")
    replacement = RefreshToken(
        uuid4(), session.session_id, token.created_at + 1, token.expires_at
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        logout = pool.submit(
            repository.revoke_session,
            session.session_id,
            user_id,
            token.created_at + 2,
        )
        refresh = pool.submit(
            repository.rotate_refresh_token,
            session.session_id,
            token.jti,
            replacement,
            token.created_at + 1,
        )
        assert logout.result(timeout=5) is True
        assert refresh.result(timeout=5) in {ROTATED, INACTIVE}

    stored_session = repository.get_session(session.session_id)
    with engine.connect() as connection:
        active = connection.execute(
            text("SELECT active FROM push_subscriptions WHERE subscription_id = :id"),
            {"id": subscription.subscription_id},
        ).scalar_one()
    assert stored_session is not None and stored_session.revoked_at is not None
    assert active is False
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT count(*) FROM refresh_tokens "
                "WHERE session_id = :session_id AND revoked_at IS NULL"
            ),
            {"session_id": session.session_id},
        ).scalar_one() == 0
