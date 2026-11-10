from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.adapters.shift_reports import lifecycle_notifications as lifecycle


@pytest.mark.parametrize("event", ["created", "approved", "opened", "closed"])
def test_lifecycle_content_and_recipient(monkeypatch, event):
    performer, foreman, shift_id = uuid4(), uuid4(), uuid4()
    report = SimpleNamespace(user=performer, project=uuid4(), shift_report_id=shift_id, number=42)
    captured = []
    class Query:
        def filter(self, *args):
            return self
        def scalar(self):
            return foreman
    class Session:
        def query(self, *args):
            return Query()
    monkeypatch.setattr(lifecycle.CreateNotificationUseCase, "execute", lambda self, command: captured.append(command))
    lifecycle.notify_shift_event(Session(), report, event, performer, uuid4())
    command = captured[0]
    assert command.notification_type == f"shift_report.{event}"
    assert command.recipient_user_ids == ((performer if event in ("created", "approved") else foreman),)
    assert "42" in command.text
    assert command.link is None
    assert command.related_entity_id == str(shift_id)


def test_no_foreman_skips_notification(monkeypatch):
    class Query:
        def filter(self, *args): return self
        def scalar(self): return None
    class Session:
        def query(self, *args): return Query()
    def fail(*args):
        raise AssertionError("notification should not be created")
    monkeypatch.setattr(lifecycle.CreateNotificationUseCase, "execute", fail)
    lifecycle.notify_shift_event(Session(), SimpleNamespace(project=uuid4()), "opened", uuid4(), uuid4())
