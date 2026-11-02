"""PostgreSQL checks use a disposable schema in TEST_DATABASE_URL."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, event, func, inspect, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session, sessionmaker

from app.adapters.notifications import SQLAlchemyNotificationRepository
from app.database import db_globals
from app.database.db_setup import Base
from app.database.models import Roles, Users
from app.database.models.notifications import NotificationRecipients, Notifications
from app.domain.notifications import NotificationIdempotencyConflictError
from app.use_cases.notifications import (
    CreateNotificationCommand,
    CreateNotificationUseCase,
    CountUnviewedNotificationsUseCase,
    GetOwnNotificationUseCase,
    ListNotificationHistoryUseCase,
    ListUnviewedNotificationsUseCase,
    MarkNotificationViewedUseCase,
)


@pytest.fixture
def notification_db(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL checks")
    schema = "notifications_" + uuid4().hex
    admin_engine = create_engine(url)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def set_schema(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f'SET search_path TO "{schema}"')
        cursor.close()

    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        db_globals, "Session", scoped_session(sessionmaker(bind=engine))
    )
    try:
        yield engine
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def test_create_notification_is_atomic_and_view_is_owned_and_idempotent(
    notification_db,
):
    factory = sessionmaker(bind=notification_db)
    user_id = uuid4()
    with factory.begin() as session:
        session.add(Roles(role_id="notifications-test", name="Test"))
        session.add(
            Users(
                user_id=user_id,
                login=str(user_id),
                password_hash="unused",
                name="Test",
                role="notifications-test",
                created_by=user_id,
            )
        )
    repository = SQLAlchemyNotificationRepository()
    notification = CreateNotificationUseCase(repository).execute(
        CreateNotificationCommand("event:one", "event", "Title", "Text", (user_id,))
    )
    owner_browser, other_browser = uuid4(), uuid4()
    use_case = MarkNotificationViewedUseCase(repository)

    first = use_case.execute(notification.notification_id, user_id, owner_browser)
    repeated = use_case.execute(notification.notification_id, user_id, other_browser)
    unowned = use_case.execute(notification.notification_id, uuid4(), uuid4())

    assert first is not None and first.viewed is True
    assert first.viewed_at is not None and first.viewed_at > 0
    assert first.browser_id == owner_browser
    assert repeated == first
    assert unowned is None


def test_two_devices_record_only_the_first_view(notification_db):
    factory = sessionmaker(bind=notification_db)
    user_id = uuid4()
    with factory.begin() as session:
        session.add(Roles(role_id="notifications-test", name="Test"))
        session.add(
            Users(
                user_id=user_id,
                login=str(user_id),
                password_hash="unused",
                name="Test",
                role="notifications-test",
                created_by=user_id,
            )
        )
    repository = SQLAlchemyNotificationRepository()
    notification = CreateNotificationUseCase(repository).execute(
        CreateNotificationCommand("event:two", "event", "Title", "Text", (user_id,))
    )
    barrier = Barrier(2)

    def view(browser_id):
        barrier.wait(timeout=5)
        return MarkNotificationViewedUseCase(repository).execute(
            notification.notification_id, user_id, browser_id
        )

    browsers = (uuid4(), uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(view, browsers))

    assert results[0] == results[1]
    assert results[0] is not None
    assert results[0].viewed_at is not None and results[0].viewed_at > 0
    assert results[0].browser_id in browsers


def test_same_idempotency_key_is_safe_under_concurrent_creation(notification_db):
    factory = sessionmaker(bind=notification_db)
    user_id = uuid4()
    with factory.begin() as session:
        session.add(Roles(role_id="notifications-test", name="Test"))
        session.add(
            Users(
                user_id=user_id,
                login=str(user_id),
                password_hash="unused",
                name="Test",
                role="notifications-test",
                created_by=user_id,
            )
        )
    repository = SQLAlchemyNotificationRepository()
    command = CreateNotificationCommand(
        "shift.completed:history-123", "shift.completed", "Title", "Text", (user_id,)
    )
    barrier = Barrier(2)

    def create():
        barrier.wait(timeout=5)
        return CreateNotificationUseCase(repository).execute(command)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: create(), range(2)))

    assert results[0] == results[1]
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Notifications)) == 1
        assert session.scalar(select(func.count()).select_from(NotificationRecipients)) == 1


def test_idempotency_mismatch_conflicts_and_different_keys_are_independent(
    notification_db,
):
    factory = sessionmaker(bind=notification_db)
    user_id, additional_user_id = uuid4(), uuid4()
    with factory.begin() as session:
        session.add(Roles(role_id="notifications-test", name="Test"))
        for user_id_value in (user_id, additional_user_id):
            session.add(
                Users(
                    user_id=user_id_value,
                    login=str(user_id_value),
                    password_hash="unused",
                    name="Test",
                    role="notifications-test",
                    created_by=user_id_value,
                )
            )
    repository = SQLAlchemyNotificationRepository()
    create = CreateNotificationUseCase(repository)
    original = create.execute(
        CreateNotificationCommand("evt-1", "event", "Title", "Text", (user_id,))
    )
    replay = create.execute(
        CreateNotificationCommand("evt-1", "event", "Title", "Text", (user_id,))
    )
    assert replay.notification_id == original.notification_id
    with pytest.raises(NotificationIdempotencyConflictError):
        create.execute(
            CreateNotificationCommand(
                "evt-1", "event", "Changed", "Text", (user_id, additional_user_id)
            )
        )
    independent = create.execute(
        CreateNotificationCommand("evt-2", "event", "Title", "Text", (user_id,))
    )
    assert independent.notification_id != original.notification_id
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Notifications)) == 2
        assert session.scalar(select(func.count()).select_from(NotificationRecipients)) == 2


def test_read_operations_are_owned_and_use_stable_pagination(notification_db):
    factory = sessionmaker(bind=notification_db)
    user_id, other_user_id = uuid4(), uuid4()
    with factory.begin() as session:
        session.add(Roles(role_id="notifications-test", name="Test"))
        for user_id_value in (user_id, other_user_id):
            session.add(
                Users(
                    user_id=user_id_value,
                    login=str(user_id_value),
                    password_hash="unused",
                    name="Test",
                    role="notifications-test",
                    created_by=user_id_value,
                )
            )
    repository = SQLAlchemyNotificationRepository()
    create = CreateNotificationUseCase(repository)
    created = [
        create.execute(
            CreateNotificationCommand(
                f"history:{index}", "event", f"Title {index}", "Text", (user_id,)
            )
        )
        for index in range(3)
    ]
    # Force a timestamp tie so the UUID tie-breaker is exercised directly.
    with factory.begin() as session:
        session.execute(
            update(Notifications)
            .where(Notifications.notification_id.in_([item.notification_id for item in created]))
            .values(created_at=1234567890000)
        )
    history = ListNotificationHistoryUseCase(repository)
    page_one = history.execute(user_id, limit=2)
    page_two = history.execute(user_id, offset=2, limit=2)
    all_ids = [item.notification_id for item in page_one + page_two]
    expected = sorted((item.notification_id for item in created), reverse=True)
    assert all_ids == expected
    assert CountUnviewedNotificationsUseCase(repository).execute(user_id) == 3
    assert len(ListUnviewedNotificationsUseCase(repository).execute(user_id)) == 3
    assert GetOwnNotificationUseCase(repository).execute(created[0].notification_id, user_id)
    assert GetOwnNotificationUseCase(repository).execute(created[0].notification_id, other_user_id) is None
    marked = MarkNotificationViewedUseCase(repository).execute(
        created[0].notification_id, user_id, uuid4()
    )
    assert marked is not None
    assert CountUnviewedNotificationsUseCase(repository).execute(user_id) == 2
    assert CountUnviewedNotificationsUseCase(repository).execute(other_user_id) == 0


def test_idempotency_migration_preserves_rows_and_enforces_unique_key():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL checks")
    migration_path = (
        Path(__file__).parents[1]
        / "alembic/versions/20261103120000_notification_idempotency.py"
    )
    spec = spec_from_file_location("notification_idempotency_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine(url, connect_args={"connect_timeout": 3})
    schema = "notification_migration_" + uuid4().hex
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        isolated = create_engine(
            url,
            connect_args={"connect_timeout": 3, "options": f"-csearch_path={schema}"},
        )
        try:
            with isolated.begin() as connection:
                connection.execute(text(
                    "CREATE TABLE notifications (notification_id UUID PRIMARY KEY, notification_type VARCHAR(100) NOT NULL)"
                ))
                connection.execute(text(
                    "INSERT INTO notifications (notification_id, notification_type) VALUES (:id, 'legacy')"
                ), {"id": uuid4()})
                with Operations.context(MigrationContext.configure(connection)):
                    migration.upgrade()
                assert connection.scalar(text("SELECT count(*) FROM notifications")) == 1
                connection.execute(text(
                    "INSERT INTO notifications (notification_id, notification_type, idempotency_key) VALUES (:id, 'new', 'stable-key')"
                ), {"id": uuid4()})
                with pytest.raises(IntegrityError), connection.begin_nested():
                    connection.execute(text(
                        "INSERT INTO notifications (notification_id, notification_type, idempotency_key) VALUES (:id, 'new', 'stable-key')"
                    ), {"id": uuid4()})
                with Operations.context(MigrationContext.configure(connection)):
                    migration.downgrade()
                assert "idempotency_key" not in [
                    column["name"] for column in inspect(connection).get_columns("notifications")
                ]
        finally:
            isolated.dispose()
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
