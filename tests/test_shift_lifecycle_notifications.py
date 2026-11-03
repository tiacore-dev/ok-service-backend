from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest

from app.adapters.shift_reports.lifecycle_notifications import notify_shift_event
from app.database.managers.shift_reports_managers import ShiftReportsManager
from app.database.models import NotificationRecipients, Notifications, Projects, ShiftReports
from app.domain.shift_reports import ShiftReportConflictError


def _create(seed_user, seed_project, manager=None):
    return (manager or ShiftReportsManager()).add_shift_report_with_details(
        {"user": seed_user["user_id"], "project": seed_project["project_id"], "date": 20240101},
        seed_user["user_id"],
    )


def _events(session, report_id):
    return session.query(Notifications).filter_by(related_entity_id=str(report_id)).order_by(Notifications.created_at, Notifications.notification_type).all()


def test_create_and_approval_are_atomic_and_replays_do_not_duplicate(db_session, seed_user, seed_project):
    report = _create(seed_user, seed_project)
    report_id = UUID(report["shift_report_id"])
    manager = ShiftReportsManager()
    manager.sign_shift_report(report_id, UUID(seed_user["user_id"]))
    manager.sign_shift_report(report_id, UUID(seed_user["user_id"]))
    db_session.expire_all()
    events = _events(db_session, report_id)
    assert {e.notification_type for e in events} == {"shift_report.created", "shift_report.approved"}
    assert len(events) == 2
    assert all(db_session.query(NotificationRecipients).filter_by(notification_id=e.notification_id, user_id=UUID(seed_user["user_id"])).count() == 1 for e in events)
    record = db_session.get(ShiftReports, report_id)
    notify_shift_event(db_session, record, "created", UUID(seed_user["user_id"]), report_id)
    db_session.commit()
    assert len(_events(db_session, report_id)) == 2


def test_missing_foreman_and_manual_edits_do_not_send(db_session, seed_user, seed_project):
    project = db_session.get(Projects, UUID(seed_project["project_id"]))
    project.project_leader = None
    db_session.commit()
    report = _create(seed_user, seed_project)
    rid = UUID(report["shift_report_id"])
    manager = ShiftReportsManager()
    manager.update_shift_report(rid, lifecycle_operation="start", lifecycle_actor_role="admin", updated_by=UUID(seed_user["user_id"]), date_start=10)
    manager.update_shift_report(rid, lifecycle_operation="finish", lifecycle_actor_role="admin", updated_by=UUID(seed_user["user_id"]), date_end=20)
    manager.update_shift_report(rid, signed=True)
    assert [e.notification_type for e in _events(db_session, rid)] == ["shift_report.created"]


def test_start_finish_and_fresh_occurrences_notify_only_assigned_foreman(db_session, seed_user, seed_leader, seed_project):
    project = db_session.get(Projects, UUID(seed_project["project_id"]))
    project.project_leader = UUID(seed_leader["user_id"])
    db_session.commit()
    report = _create(seed_user, seed_project)
    rid = UUID(report["shift_report_id"])
    manager = ShiftReportsManager()
    for cycle in range(2):
        manager.update_shift_report(rid, lifecycle_operation="start", lifecycle_actor_role="admin", updated_by=UUID(seed_user["user_id"]), date_start=10)
        with pytest.raises(ShiftReportConflictError):
            manager.update_shift_report(rid, lifecycle_operation="start", lifecycle_actor_role="admin", updated_by=UUID(seed_user["user_id"]), date_start=10)
        manager.update_shift_report(rid, lifecycle_operation="finish", lifecycle_actor_role="admin", updated_by=UUID(seed_user["user_id"]), date_end=20)
        if cycle == 0:
            db_session.expire_all()
            row = db_session.get(ShiftReports, rid)
            row.date_start = row.date_end = None
            db_session.commit()
    db_session.expire_all()
    events = _events(db_session, rid)
    lifecycle = [e for e in events if e.notification_type in ("shift_report.opened", "shift_report.closed")]
    assert len(lifecycle) == 4
    assert len({e.idempotency_key for e in lifecycle}) == 4
    for event in lifecycle:
        recipients = db_session.query(NotificationRecipients).filter_by(notification_id=event.notification_id).all()
        assert [r.user_id for r in recipients] == [UUID(seed_leader["user_id"])]
        assert recipients[0].viewed is False


def test_notification_failure_rolls_back_shift(db_session, seed_user, seed_project, monkeypatch):
    from app.adapters.shift_reports import lifecycle_notifications
    def fail(*args, **kwargs):
        raise RuntimeError("notification failure")
    monkeypatch.setattr(lifecycle_notifications.CreateNotificationUseCase, "execute", fail)
    with pytest.raises(RuntimeError, match="notification failure"):
        _create(seed_user, seed_project)
    db_session.expire_all()
    assert db_session.query(ShiftReports).count() == 0
    assert db_session.query(Notifications).count() == 0


def test_concurrent_start_creates_one_notification(db_session, seed_user, seed_project):
    report = _create(seed_user, seed_project)
    rid = UUID(report["shift_report_id"])
    barrier = Barrier(2)
    def start():
        barrier.wait(timeout=5)
        try:
            ShiftReportsManager().update_shift_report(rid, lifecycle_operation="start", lifecycle_actor_role="admin", updated_by=UUID(seed_user["user_id"]), date_start=10)
            return "ok"
        except ShiftReportConflictError:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: start(), range(2)))
    assert sorted(results) == ["conflict", "ok"]
    db_session.expire_all()
    assert sum(e.notification_type == "shift_report.opened" for e in _events(db_session, rid)) == 1


def test_delivery_created_and_processed_with_fake_provider(db_session, test_app, seed_user, seed_project):
    from app.database.models import AuthSessions, PushSubscriptions, PushDeliveries
    from app.database.time_utils import utc_epoch_milliseconds
    from app.domain.push_notifications import PushDelivery, PushDeliveryStatus
    from app.push_worker import PushWorker

    user = UUID(seed_user["user_id"])
    now = utc_epoch_milliseconds()
    auth = AuthSessions(session_id=uuid4(), user_id=user, created_at=now,
                        expires_at=now + 3600000, current_token_jti=uuid4())
    db_session.add(auth)
    db_session.flush()
    db_session.add(PushSubscriptions(user_id=user, browser_id=uuid4(), auth_session_id=auth.session_id,
                                     platform="web", token="ok45-test-token", active=True))
    db_session.commit()
    report = _create(seed_user, seed_project)
    assert db_session.query(PushDeliveries).count() == 1
    db_session.rollback()
    class Provider:
        def send(self, notification, targets):
            assert notification.title == "Назначена смена"
            assert len(targets) == 1
            return [PushDelivery(targets[0].subscription_id, PushDeliveryStatus.SENT)]
    assert PushWorker(test_app, Provider()).run_once() == 1
    db_session.expire_all()
    assert db_session.query(PushDeliveries).one().status == "sent"
    assert len(_events(db_session, report["shift_report_id"])) == 1


def test_failure_after_notification_insert_rolls_back_transition(db_session, seed_user, seed_project, monkeypatch):
    from app.adapters.shift_reports import lifecycle_notifications
    report = _create(seed_user, seed_project)
    rid = UUID(report["shift_report_id"])
    original = lifecycle_notifications.CreateNotificationUseCase.execute
    def fail_after_insert(self, command):
        original(self, command)
        raise RuntimeError("after notification insert")
    monkeypatch.setattr(lifecycle_notifications.CreateNotificationUseCase, "execute", fail_after_insert)
    with pytest.raises(RuntimeError, match="after notification insert"):
        ShiftReportsManager().update_shift_report(rid, lifecycle_operation="start", lifecycle_actor_role="admin", updated_by=UUID(seed_user["user_id"]), date_start=10)
    db_session.expire_all()
    assert db_session.get(ShiftReports, rid).date_start is None
    assert [e.notification_type for e in _events(db_session, rid)] == ["shift_report.created"]


def test_start_waits_for_shift_lock_and_rechecks_state(db_session, seed_user, seed_project):
    import time
    from sqlalchemy import text
    from app.database import db_globals

    report = _create(seed_user, seed_project)
    rid = UUID(report["shift_report_id"])
    db_session.rollback()
    engine = db_globals.engine
    with engine.connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        transaction = blocker.begin()
        pid = blocker.scalar(text("SELECT pg_backend_pid()"))
        blocker.execute(text("SELECT shift_report_id FROM shift_reports WHERE shift_report_id=:id FOR UPDATE"), {"id": rid})
        future = pool.submit(ShiftReportsManager().update_shift_report, rid,
                             lifecycle_operation="start", lifecycle_actor_role="admin",
                             updated_by=UUID(seed_user["user_id"]), date_start=10)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with engine.connect() as observer:
                blocked = observer.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE :pid = ANY(pg_blocking_pids(pid)))"), {"pid": pid})
            if blocked:
                break
            time.sleep(0.01)
        else:
            transaction.rollback()
            pytest.fail("start did not wait on the shift row lock")
        blocker.execute(text("UPDATE shift_reports SET date_start=9 WHERE shift_report_id=:id"), {"id": rid})
        transaction.commit()
        with pytest.raises(ShiftReportConflictError, match="already been started"):
            future.result(timeout=5)
    db_session.expire_all()
    assert [e.notification_type for e in _events(db_session, rid)] == ["shift_report.created"]


def test_reprocessing_same_open_occurrence_is_idempotent(db_session, seed_user, seed_project):
    report = _create(seed_user, seed_project)
    rid = UUID(report["shift_report_id"])
    row = db_session.get(ShiftReports, rid)
    occurrence = uuid4()
    actor = UUID(seed_user["user_id"])
    notify_shift_event(db_session, row, "opened", actor, occurrence)
    notify_shift_event(db_session, row, "opened", actor, occurrence)
    db_session.commit()
    events = [event for event in _events(db_session, rid) if event.notification_type == "shift_report.opened"]
    assert len(events) == 1
    assert db_session.query(NotificationRecipients).filter_by(notification_id=events[0].notification_id).count() == 1


def test_http_lifecycle_creates_notifications(client, db_session, jwt_token_admin, seed_user, seed_leader, seed_project):
    project = db_session.get(Projects, UUID(seed_project["project_id"]))
    project.project_leader = UUID(seed_leader["user_id"])
    db_session.commit()
    headers = {"Authorization": f"Bearer {jwt_token_admin}"}
    response = client.post("/shift_reports/add", headers=headers, json={
        "user": seed_user["user_id"], "project": seed_project["project_id"], "date": 20240101,
    })
    assert response.status_code == 200, response.json
    rid = response.json["shift_report_id"]
    for action in ("start", "finish"):
        response = client.patch(f"/shift_reports/{rid}/{action}", headers=headers,
                                json={"lng": 82.9, "ltd": 55.0})
        assert response.status_code == 200, response.json
    response = client.patch(f"/shift_reports/{rid}/sign", headers=headers)
    assert response.status_code == 200, response.json
    db_session.expire_all()
    events = _events(db_session, rid)
    assert {e.notification_type for e in events} == {
        "shift_report.created", "shift_report.approved", "shift_report.opened", "shift_report.closed"
    }
