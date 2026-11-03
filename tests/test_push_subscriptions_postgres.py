"""Run only with an explicitly supplied disposable PostgreSQL database."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from types import SimpleNamespace
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import scoped_session, sessionmaker

from app.adapters.auth_sessions import SQLAlchemyAuthSessionRepository
from app.adapters.push_subscriptions import SQLAlchemyPushSubscriptionRepository
from app.adapters.push_deliveries import SQLAlchemyPushDeliveryRepository
from app.adapters.notifications import SQLAlchemyNotificationRepository
from app.database import db_globals
from app.domain.auth_sessions import AuthSession, RefreshToken
from app.domain.push_notifications import PushDelivery, PushDeliveryStatus
from app.push_worker import PushWorker
from app.use_cases.notifications import CreateNotificationCommand, CreateNotificationUseCase
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
        connection.execute(text("""
            CREATE TABLE notifications (
              notification_id uuid PRIMARY KEY, notification_type varchar(100) NOT NULL,
              title varchar(255) NOT NULL, text text NOT NULL, link text,
              related_entity_type varchar(100), related_entity_id varchar(100),
              created_at bigint NOT NULL, created_by uuid,
              idempotency_key varchar(255) UNIQUE
            )
        """))
        connection.execute(text("""
            CREATE TABLE notification_recipients (
              notification_recipient_id uuid PRIMARY KEY,
              notification_id uuid NOT NULL REFERENCES notifications(notification_id) ON DELETE CASCADE,
              user_id uuid NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
              viewed boolean NOT NULL DEFAULT false, viewed_at bigint, browser_id uuid,
              CONSTRAINT uq_notification_recipients_notification_user UNIQUE (notification_id, user_id)
            )
        """))
        modules = []
        for revision in (
            "20261104120000_push_subscriptions.py",
            "20261105120000_auth_sessions.py",
            "20261106120000_bind_push_subscriptions_to_auth_sessions.py",
            "20261107120000_push_deliveries.py",
        ):
            path = Path("alembic/versions") / revision
            spec = spec_from_file_location(revision, path)
            assert spec is not None and spec.loader is not None
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            setattr(module, "op", Operations(MigrationContext.configure(connection)))
            module.upgrade()
            modules.append(module)
    monkeypatch.setattr(db_globals, "Session", scoped_session(sessionmaker(bind=engine)))
    yield engine, modules[-2]
    engine.dispose()
    with admin.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


def _session(repository, user, browser, now):
    session_id, jti = uuid4(), uuid4()
    repository.create_session_with_refresh_token(
        AuthSession(session_id, user, now, 9_000_000_000_000, jti, browser_id=browser),
        RefreshToken(jti, session_id, now, 9_000_000_000_000),
    )
    return session_id


def test_delivery_jobs_are_atomic_deduplicated_and_reclaimed_after_lease(database):
    engine, _ = database
    user, browser = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users VALUES (:id)"), {"id": user})
    auth_sessions = SQLAlchemyAuthSessionRepository()
    session_id = _session(auth_sessions, user, browser, 1)
    RegisterPushSubscription(SQLAlchemyPushSubscriptionRepository()).execute(
        user, browser, session_id, "web", "delivery-token"
    )
    notification = CreateNotificationUseCase(SQLAlchemyNotificationRepository()).execute(
        CreateNotificationCommand("delivery:event", "event", "Title", "Body", (user,))
    )
    replay = CreateNotificationUseCase(SQLAlchemyNotificationRepository()).execute(
        CreateNotificationCommand("delivery:event", "event", "Title", "Body", (user,))
    )
    assert replay.notification_id == notification.notification_id
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM push_deliveries")) == 1

    repo = SQLAlchemyPushDeliveryRepository()
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                lambda worker: (
                    barrier.wait(timeout=5),
                    repo.claim_ready(worker, 1, 1_000, 3),
                )[1],
                worker,
            )
            for worker in ("one", "two")
        ]
        claimed = [item for future in futures for item in future.result(timeout=5)]
    assert len(claimed) == 1
    first = claimed
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE push_deliveries SET locked_until = 0 WHERE delivery_id = :id"),
            {"id": first[0].delivery_id},
        )
    second = repo.claim_ready("two", 1, 1_000, 3)
    assert len(second) == 1 and second[0].delivery_id == first[0].delivery_id
    assert second[0].lease_token != first[0].lease_token and second[0].attempts == 2
    assert not repo.record_result(
        first[0], PushDeliveryStatus.SENT, max_attempts=3, retry_delay_ms=1
    )
    assert repo.record_result(
        second[0], PushDeliveryStatus.SENT, provider_message_id="message-id",
        max_attempts=3, retry_delay_ms=1,
    )
    with engine.connect() as connection:
        row = connection.execute(text("SELECT status, sent_at FROM push_deliveries")).one()
        assert row.status == "sent" and row.sent_at is not None


def test_delivery_migration_upgrade_and_downgrade(database):
    engine, _ = database
    path = Path("alembic/versions/20261107120000_push_deliveries.py")
    spec = spec_from_file_location("push_deliveries_migration", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        setattr(migration, "op", Operations(MigrationContext.configure(connection)))
        migration.downgrade()
        assert "push_deliveries" not in inspect(connection).get_table_names()
        migration.upgrade()
        assert "push_deliveries" in inspect(connection).get_table_names()


def test_registration_transfer_revocation_constraints_and_migration(database):
    engine, migration = database
    user, other, browser, second = uuid4(), uuid4(), uuid4(), uuid4()
    with engine.begin() as c:
        c.execute(text("INSERT INTO users VALUES (:a), (:b)"), {"a": user, "b": other})
    auth_sessions = SQLAlchemyAuthSessionRepository()
    repo = SQLAlchemyPushSubscriptionRepository()
    register = RegisterPushSubscription(repo)
    first_session = _session(auth_sessions, user, browser, 1)
    second_session = _session(auth_sessions, user, second, 2)
    first = register.execute(user, browser, first_session, "web", "token-1")
    repeat = register.execute(user, browser, first_session, "web", "token-2")
    assert repeat.subscription_id == first.subscription_id and repeat.token == "token-2"
    another = register.execute(user, second, second_session, "web", "token-3")
    other_session = _session(auth_sessions, other, browser, 3)
    assert another.subscription_id != first.subscription_id
    moved = register.execute(other, browser, other_session, "web", "token-2")
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
    assert register.execute(other, browser, other_session, "web", "token-2").subscription_id == moved.subscription_id
    with pytest.raises(IntegrityError), engine.begin() as c:
        c.execute(text("INSERT INTO push_subscriptions (subscription_id, user_id, browser_id, platform, token, active, created_at, updated_at) VALUES (:id, :user, :browser, 'web', 'token-4', true, 1, 1)"), {"id": uuid4(), "user": user, "browser": uuid4()})
    # A token moving to another browser revokes its prior owner atomically.
    transferred = register.execute(user, second, second_session, "web", "token-2")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT active FROM push_subscriptions WHERE subscription_id = :id"), {"id": moved.subscription_id}).scalar_one() is False
        assert connection.execute(text("SELECT active FROM push_subscriptions WHERE subscription_id = :id"), {"id": transferred.subscription_id}).scalar_one() is True
    with engine.begin() as c:
        setattr(migration, "op", Operations(MigrationContext.configure(c)))
        migration.downgrade()
        assert "auth_session_id" not in {item["name"] for item in inspect(c).get_columns("push_subscriptions")}
        migration.upgrade()
        assert "auth_session_id" in {item["name"] for item in inspect(c).get_columns("push_subscriptions")}


def test_competing_registrations_wait_and_transfer(database):
    engine, _ = database
    user, other, browser = uuid4(), uuid4(), uuid4()
    with engine.begin() as c:
        c.execute(text("INSERT INTO users VALUES (:a), (:b)"), {"a": user, "b": other})
    auth_sessions = SQLAlchemyAuthSessionRepository()
    repository = SQLAlchemyPushSubscriptionRepository()
    register = RegisterPushSubscription(repository)
    first_session = _session(auth_sessions, user, browser, 1)
    register.execute(user, browser, first_session, "web", "old")
    other_session = _session(auth_sessions, other, browser, 2)
    with engine.connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        transaction = blocker.begin()
        pid = blocker.execute(text("select pg_backend_pid()" )).scalar_one()
        blocker.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": "push:browser:" + str(browser)})
        future = pool.submit(register.execute, other, browser, other_session, "web", "new")
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


def _delivery_setup(engine):
    user, browser = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(text('INSERT INTO users VALUES (:id)'), {'id': user})
    auth = SQLAlchemyAuthSessionRepository()
    sid = _session(auth, user, browser, 1)
    register = RegisterPushSubscription(SQLAlchemyPushSubscriptionRepository())
    subscription = register.execute(user, browser, sid, 'web', 'token-A-private')
    create = CreateNotificationUseCase(SQLAlchemyNotificationRepository())
    def enqueue(key):
        return create.execute(CreateNotificationCommand(key, 'event', 'Title', 'Body', (user,)))
    return user, browser, sid, subscription, register, enqueue


def _worker_app():
    return SimpleNamespace(config={
        'PUSH_WORKER_BATCH_SIZE': 10, 'PUSH_WORKER_LEASE_SECONDS': 60,
        'PUSH_WORKER_MAX_ATTEMPTS': 3, 'PUSH_WORKER_RETRY_BASE_SECONDS': 2,
        'PUSH_WORKER_RETRY_MAX_SECONDS': 30, 'PUSH_WORKER_POLL_INTERVAL_SECONDS': 1,
    })


def test_skip_locked_selects_other_row_while_first_is_locked(database):
    engine, _ = database
    *_, enqueue = _delivery_setup(engine)
    enqueue('skip-one')
    enqueue('skip-two')
    repo = SQLAlchemyPushDeliveryRepository()
    with engine.connect() as blocker:
        transaction = blocker.begin()
        locked = blocker.scalar(text('SELECT delivery_id FROM push_deliveries ORDER BY next_attempt_at, delivery_id LIMIT 1 FOR UPDATE'))
        with ThreadPoolExecutor(max_workers=1) as pool:
            claimed = pool.submit(repo.claim_ready, 'other', 1, 60000, 3).result(timeout=5)
        assert len(claimed) == 1 and claimed[0].delivery_id != locked
        transaction.rollback()
    assert repo.claim_ready('other', 1, 60000, 3)[0].delivery_id == locked


def test_expired_lease_rejects_invalid_token_before_reclaim(database):
    engine, _ = database
    _, _, _, subscription, _, enqueue = _delivery_setup(engine)
    enqueue('expired')
    repo = SQLAlchemyPushDeliveryRepository()
    first = repo.claim_ready('first', 1, 60000, 3)[0]
    with engine.begin() as connection:
        connection.execute(text('UPDATE push_deliveries SET locked_until=0 WHERE delivery_id=:id'), {'id': first.delivery_id})
    assert not repo.record_result(first, PushDeliveryStatus.INVALID_TOKEN, max_attempts=3, retry_delay_ms=1)
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT active FROM push_subscriptions WHERE subscription_id=:id'), {'id': subscription.subscription_id})
        assert connection.scalar(text('SELECT status FROM push_deliveries')) == 'processing'
    second = repo.claim_ready('second', 1, 60000, 3)[0]
    assert second.lease_token != first.lease_token
    assert not repo.record_result(first, PushDeliveryStatus.SENT, max_attempts=3, retry_delay_ms=1)
    assert repo.record_result(second, PushDeliveryStatus.SENT, max_attempts=3, retry_delay_ms=1)
    assert not repo.record_result(second, PushDeliveryStatus.SENT, max_attempts=3, retry_delay_ms=1)


def test_current_invalid_token_deactivates_subscription(database):
    engine, _ = database
    _, _, _, subscription, _, enqueue = _delivery_setup(engine)
    enqueue('invalid-current')
    repo = SQLAlchemyPushDeliveryRepository()
    delivery = repo.claim_ready('worker', 1, 60000, 3)[0]
    assert repo.record_result(delivery, PushDeliveryStatus.INVALID_TOKEN, max_attempts=3, retry_delay_ms=1)
    with engine.connect() as connection:
        assert not connection.scalar(text('SELECT active FROM push_subscriptions WHERE subscription_id=:id'), {'id': subscription.subscription_id})
        assert connection.scalar(text('SELECT status FROM push_deliveries')) == 'failed'


def test_token_rotation_during_provider_call_does_not_revoke_new_token(database, caplog):
    engine, _ = database
    user, browser, sid, subscription, register, enqueue = _delivery_setup(engine)
    enqueue('rotation')
    entered, resume = Event(), Event()
    class Provider:
        def send(self, notification, targets):
            assert engine.pool.checkedout() == 0
            entered.set()
            assert resume.wait(5)
            return [PushDelivery(targets[0].subscription_id, PushDeliveryStatus.INVALID_TOKEN)]
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(PushWorker(_worker_app(), Provider()).run_once)
        try:
            assert entered.wait(5)
            register.execute(user, browser, sid, 'web', 'token-B-private')
        finally:
            resume.set()
        assert future.result(timeout=5) == 1
    with engine.connect() as connection:
        row = connection.execute(text('SELECT active, token FROM push_subscriptions WHERE subscription_id=:id'), {'id': subscription.subscription_id}).one()
        assert row.active and row.token == 'token-B-private'
    assert 'token-A-private' not in caplog.text and 'token-B-private' not in caplog.text


def test_logout_after_claim_before_send_skips_provider(database):
    engine, _ = database
    user, _, sid, _, _, enqueue = _delivery_setup(engine)
    enqueue('logout')
    class Repo(SQLAlchemyPushDeliveryRepository):
        def claim_ready(self, *args):
            result = super().claim_ready(*args)
            assert SQLAlchemyAuthSessionRepository().revoke_session(sid, user, 100)
            return result
    class Provider:
        def send(self, *_args):
            pytest.fail('provider must not be called after logout')
    assert PushWorker(_worker_app(), Provider(), Repo()).run_once() == 1
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT status FROM push_deliveries')) == 'failed'


def test_notification_and_recipients_roll_back_when_delivery_insert_fails(database):
    engine, _ = database
    *_, enqueue = _delivery_setup(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE FUNCTION reject_delivery() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test failure'; END $$"))
        connection.execute(text('CREATE TRIGGER reject_delivery BEFORE INSERT ON push_deliveries FOR EACH ROW EXECUTE FUNCTION reject_delivery()'))
    with pytest.raises(DBAPIError, match='test failure'):
        enqueue('rollback')
    with engine.connect() as connection:
        for table in ('notifications', 'notification_recipients', 'push_deliveries'):
            assert connection.scalar(text(f'SELECT count(*) FROM {table}')) == 0


def test_retry_is_persisted_and_waits_until_due(database):
    engine, _ = database
    *_, enqueue = _delivery_setup(engine)
    enqueue('retry')
    repo = SQLAlchemyPushDeliveryRepository()
    first = repo.claim_ready('first', 1, 60000, 3)[0]
    assert repo.record_result(first, PushDeliveryStatus.TEMPORARY_FAILURE, max_attempts=3, retry_delay_ms=60000)
    assert repo.claim_ready('second', 1, 60000, 3) == []
    with engine.begin() as connection:
        assert connection.scalar(text('SELECT status FROM push_deliveries')) == 'retry'
        connection.execute(text('UPDATE push_deliveries SET next_attempt_at=0'))
    second = repo.claim_ready('second', 1, 60000, 3)[0]
    assert second.attempts == 2
    assert repo.record_result(second, PushDeliveryStatus.CONFIGURATION_ERROR, max_attempts=2, retry_delay_ms=60000)
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT status FROM push_deliveries')) == 'failed'
        assert connection.scalar(text('SELECT active FROM push_subscriptions'))


def test_expiration_while_waiting_for_row_lock_rejects_confirmation(database):
    engine, _ = database
    *_, enqueue = _delivery_setup(engine)
    enqueue('lock-wait')
    repo = SQLAlchemyPushDeliveryRepository()
    delivery = repo.claim_ready('worker', 1, 60000, 3)[0]
    with engine.connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        transaction = blocker.begin()
        pid = blocker.scalar(text('SELECT pg_backend_pid()'))
        blocker.execute(text('UPDATE push_deliveries SET locked_until=0 WHERE delivery_id=:id'), {'id': delivery.delivery_id})
        future = pool.submit(repo.record_result, delivery, PushDeliveryStatus.SENT, max_attempts=3, retry_delay_ms=1)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with engine.connect() as observer:
                blocked = observer.scalar(text('SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE :pid = ANY(pg_blocking_pids(pid)))'), {'pid': pid})
            if blocked:
                break
            time.sleep(0.01)
        else:
            transaction.rollback()
            pytest.fail('confirmation did not wait for the locked delivery')
        transaction.commit()
        assert not future.result(timeout=5)
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT status FROM push_deliveries')) == 'processing'


def test_slow_provider_result_is_discarded_after_expiration(database, caplog):
    engine, _ = database
    _, _, _, subscription, _, enqueue = _delivery_setup(engine)
    enqueue('slow')
    class Provider:
        def send(self, notification, targets):
            assert engine.pool.checkedout() == 0
            with engine.begin() as connection:
                connection.execute(text('UPDATE push_deliveries SET locked_until=0'))
            return [PushDelivery(targets[0].subscription_id, PushDeliveryStatus.INVALID_TOKEN)]
    assert PushWorker(_worker_app(), Provider()).run_once() == 1
    assert 'lease is no longer valid' in caplog.text
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT active FROM push_subscriptions WHERE subscription_id=:id'), {'id': subscription.subscription_id})
        assert connection.scalar(text('SELECT status FROM push_deliveries')) == 'processing'
    assert len(SQLAlchemyPushDeliveryRepository().claim_ready('recovery', 1, 60000, 3)) == 1


def test_logout_during_provider_call_does_not_reactivate_subscription(database):
    engine, _ = database
    user, _, sid, subscription, _, enqueue = _delivery_setup(engine)
    enqueue('logout-inflight')
    entered, resume = Event(), Event()
    class Provider:
        def send(self, notification, targets):
            entered.set()
            assert resume.wait(5)
            return [PushDelivery(targets[0].subscription_id, PushDeliveryStatus.SENT)]
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(PushWorker(_worker_app(), Provider()).run_once)
        try:
            assert entered.wait(5)
            assert SQLAlchemyAuthSessionRepository().revoke_session(sid, user, 100)
        finally:
            resume.set()
        assert future.result(timeout=5) == 1
    with engine.connect() as connection:
        assert not connection.scalar(text('SELECT active FROM push_subscriptions WHERE subscription_id=:id'), {'id': subscription.subscription_id})
        assert connection.scalar(text('SELECT status FROM push_deliveries')) == 'sent'


def test_multiple_deliveries_have_distinct_ids_and_replay_is_idempotent(database):
    engine, _ = database
    user, _, _, _, register, enqueue = _delivery_setup(engine)
    other_browser = uuid4()
    other_session = _session(SQLAlchemyAuthSessionRepository(), user, other_browser, 1)
    register.execute(user, other_browser, other_session, 'web', 'second-private-token')
    notification = enqueue('multiple-deliveries')
    assert enqueue('multiple-deliveries').notification_id == notification.notification_id
    with engine.connect() as connection:
        rows = connection.execute(text('SELECT delivery_id, subscription_id, created_at, next_attempt_at, updated_at FROM push_deliveries')).all()
    assert len(rows) == 2
    assert len({row.delivery_id for row in rows}) == 2
    assert len({row.subscription_id for row in rows}) == 2
    assert all(row.created_at == notification.created_at == row.next_attempt_at == row.updated_at for row in rows)


def test_worker_checks_logout_after_previous_send_before_claiming_next(database):
    engine, _ = database
    user, _, sid, _, _, enqueue = _delivery_setup(engine)
    enqueue('first-notification')
    enqueue('second-notification')
    calls = []
    class Provider:
        def send(self, notification, targets):
            calls.append(notification.notification_id)
            assert SQLAlchemyAuthSessionRepository().revoke_session(sid, user, 100)
            return [PushDelivery(targets[0].subscription_id, PushDeliveryStatus.SENT)]
    assert PushWorker(_worker_app(), Provider()).run_once() == 2
    assert len(calls) == 1
    with engine.connect() as connection:
        assert sorted(connection.scalars(text('SELECT status FROM push_deliveries')).all()) == ['failed', 'sent']
