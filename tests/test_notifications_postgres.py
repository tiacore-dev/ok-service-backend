"""PostgreSQL checks use a disposable schema in TEST_DATABASE_URL."""

from __future__ import annotations

import os
import time
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
        old_autocommit = dbapi_connection.autocommit
        dbapi_connection.autocommit = True
        cursor = dbapi_connection.cursor()
        cursor.execute(f'SET search_path TO "{schema}"')
        cursor.close()
        dbapi_connection.autocommit = old_autocommit

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


def test_admin_bulk_concurrent_retry_and_invalid_recipient(notification_db):
    from app.adapters.notifications.bulk_repository import BulkNotificationRepository
    from app.use_cases.notifications.bulk import BulkNotificationUseCase, BulkRecipientsError

    factory = sessionmaker(bind=notification_db)
    actor, recipient = uuid4(), uuid4()
    with factory.begin() as session:
        session.add(Roles(role_id="admin", name="Admin"))
        session.add_all([Users(user_id=uid, login=str(uid), password_hash="unused", name="Test",
                               role="admin", created_by=uid) for uid in (actor, recipient)])
    barrier = Barrier(2)

    def send():
        barrier.wait(timeout=10)
        repo = BulkNotificationRepository(actor)
        result = BulkNotificationUseCase(repo).execute(actor, (recipient,), "title", "text", None, "key")
        return result.notification_id, repo.was_replay

    with notification_db.connect() as blocker, ThreadPoolExecutor(max_workers=2) as executor:
        transaction = blocker.begin()
        pid = blocker.scalar(text('SELECT pg_backend_pid()'))
        blocker.execute(text('SELECT user_id FROM users WHERE user_id IN (:actor, :recipient) ORDER BY user_id FOR UPDATE'), {'actor': actor, 'recipient': recipient})
        futures = [executor.submit(send) for _ in range(2)]
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with notification_db.connect() as observer:
                waiting = observer.scalar(text('SELECT count(*) FROM pg_stat_activity WHERE :pid = ANY(pg_blocking_pids(pid))'), {'pid': pid})
            if waiting >= 1 and all(not future.done() for future in futures):
                break
            time.sleep(0.01)
        else:
            transaction.rollback()
            pytest.fail('both requests did not wait for the administrator lock')
        transaction.commit()
        results = [future.result(timeout=10) for future in futures]
    assert results[0][0] == results[1][0]
    assert sorted(replayed for _, replayed in results) == [False, True]
    with pytest.raises(NotificationIdempotencyConflictError):
        BulkNotificationUseCase(BulkNotificationRepository(actor)).execute(actor, (recipient,), "different", "text", None, "key")
    with pytest.raises(BulkRecipientsError):
        BulkNotificationUseCase(BulkNotificationRepository(actor)).execute(actor, (recipient, uuid4()), "title", "text", None, "invalid")
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Notifications)) == 1
        assert session.scalar(select(func.count()).select_from(NotificationRecipients)) == 1
    with factory.begin() as session:
        session.execute(update(Users).where(Users.user_id == recipient).values(is_active=False))
    with pytest.raises(BulkRecipientsError):
        BulkNotificationUseCase(BulkNotificationRepository(actor)).execute(actor, (recipient,), "title", "text", None, "key")


def test_admin_bulk_enqueues_and_worker_processes_with_fake_provider(notification_db):
    from types import SimpleNamespace
    from app.adapters.auth_sessions import SQLAlchemyAuthSessionRepository
    from app.adapters.notifications.bulk_repository import BulkNotificationRepository
    from app.adapters.push_subscriptions import SQLAlchemyPushSubscriptionRepository
    from app.database.models.push_deliveries import PushDeliveries
    from app.domain.auth_sessions import AuthSession, RefreshToken
    from app.domain.push_notifications import PushDelivery, PushDeliveryStatus
    from app.push_worker import PushWorker
    from app.use_cases.notifications.bulk import BulkNotificationUseCase
    from app.use_cases.push_subscriptions import RegisterPushSubscription

    actor, recipient, browser, sid, jti = (uuid4() for _ in range(5))
    factory = sessionmaker(bind=notification_db)
    with factory.begin() as session:
        session.add(Roles(role_id="admin", name="Admin"))
        session.add_all([Users(user_id=uid, login=str(uid), password_hash="unused", name="Test",
                               role="admin", created_by=uid) for uid in (actor, recipient)])
    SQLAlchemyAuthSessionRepository().create_session_with_refresh_token(
        AuthSession(sid, recipient, 1, 9_000_000_000_000, jti, browser_id=browser),
        RefreshToken(jti, sid, 1, 9_000_000_000_000))
    RegisterPushSubscription(SQLAlchemyPushSubscriptionRepository()).execute(recipient, browser, sid, 'web', 'test-token')
    use_case = BulkNotificationUseCase(BulkNotificationRepository(actor))
    with notification_db.begin() as connection:
        connection.execute(text("CREATE FUNCTION reject_bulk_delivery() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'delivery failure'; END $$"))
        connection.execute(text('CREATE TRIGGER reject_bulk_delivery BEFORE INSERT ON push_deliveries FOR EACH ROW EXECUTE FUNCTION reject_bulk_delivery()'))
    from sqlalchemy.exc import DBAPIError
    with pytest.raises(DBAPIError):
        use_case.execute(actor, (recipient, actor), 'title', 'text', '/path', 'rollback-test')
    with notification_db.begin() as connection:
        assert connection.scalar(text('SELECT count(*) FROM notifications')) == 0
        assert connection.scalar(text('SELECT count(*) FROM notification_recipients')) == 0
        assert connection.scalar(text('SELECT count(*) FROM push_deliveries')) == 0
        connection.execute(text('DROP TRIGGER reject_bulk_delivery ON push_deliveries'))
    first = use_case.execute(actor, (recipient, actor), 'title', 'text', '/path', 'worker-test')
    use_case.execute(actor, (recipient, actor), 'title', 'text', '/path', 'worker-test')
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(PushDeliveries)) == 1
        assert session.scalar(select(func.count()).select_from(NotificationRecipients)) == 2

    class Provider:
        calls = 0
        def send(self, notification, targets):
            self.calls += 1
            return [PushDelivery(targets[0].subscription_id, PushDeliveryStatus.SENT)]
    provider = Provider()
    app = SimpleNamespace(config={'PUSH_WORKER_BATCH_SIZE': 10, 'PUSH_WORKER_LEASE_SECONDS': 60,
        'PUSH_WORKER_MAX_ATTEMPTS': 3, 'PUSH_WORKER_RETRY_BASE_SECONDS': 2,
        'PUSH_WORKER_RETRY_MAX_SECONDS': 30, 'PUSH_WORKER_POLL_INTERVAL_SECONDS': 1})
    assert PushWorker(app, provider).run_once() == 1
    assert provider.calls == 1
    with factory() as session:
        assert session.scalar(select(PushDeliveries.status)) == 'sent'
        assert session.get(Notifications, first.notification_id) is not None


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
