from uuid import uuid4

import pytest

from app.domain.notifications import (
    NotificationRecipientsRequiredError,
    NotificationValidationError,
)
from app.use_cases.notifications import (
    CreateNotificationCommand,
    CreateNotificationUseCase,
    MarkNotificationViewedUseCase,
)


class FakeNotificationRepository:
    def __init__(self):
        self.created = None
        self.recipients = None
        self.marked = None
        self.read_calls = []

    def create_notification(self, notification, recipient_user_ids):
        self.created = notification
        self.recipients = recipient_user_ids
        return notification

    def mark_viewed(self, notification_id, user_id, browser_id):
        self.marked = (notification_id, user_id, browser_id)

    def list_history(self, user_id, offset, limit):
        self.read_calls.append(("history", user_id, offset, limit))
        return []

    def list_unviewed(self, user_id, offset, limit):
        self.read_calls.append(("unviewed", user_id, offset, limit))
        return []

    def count_unviewed(self, user_id):
        self.read_calls.append(("count", user_id))
        return 0

    def get_for_user(self, notification_id, user_id):
        self.read_calls.append(("get", notification_id, user_id))


def test_create_notification_passes_unique_recipients_to_repository():
    repository = FakeNotificationRepository()
    first, second = uuid4(), uuid4()
    command = CreateNotificationCommand(
        idempotency_key="project.updated:event-1",
        notification_type="project.updated",
        title="Updated",
        text="Project changed",
        recipient_user_ids=(first, second, first),
    )

    result = CreateNotificationUseCase(repository).execute(command)

    assert result is repository.created
    assert repository.recipients == (first, second)
    assert result.created_at > 0


def test_create_notification_rejects_empty_recipients():
    repository = FakeNotificationRepository()
    command = CreateNotificationCommand("event-1", "event", "title", "text", ())

    with pytest.raises(NotificationRecipientsRequiredError):
        CreateNotificationUseCase(repository).execute(command)

    assert repository.created is None


@pytest.mark.parametrize(
    "changes",
    [
        {"notification_type": "t" * 101},
        {"title": "t" * 256},
        {"related_entity_type": "entity"},
        {"related_entity_id": "42"},
        {"related_entity_type": "e" * 101, "related_entity_id": "42"},
        {"related_entity_type": "entity", "related_entity_id": "i" * 101},
    ],
)
def test_create_notification_rejects_values_outside_database_constraints(changes):
    from dataclasses import replace

    repository = FakeNotificationRepository()
    command = CreateNotificationCommand(
        idempotency_key="event-1",
        notification_type="event",
        title="title",
        text="text",
        recipient_user_ids=(uuid4(),),
    )

    with pytest.raises(NotificationValidationError):
        CreateNotificationUseCase(repository).execute(replace(command, **changes))

    assert repository.created is None


def test_create_notification_strips_key_before_length_validation():
    repository = FakeNotificationRepository()
    command = CreateNotificationCommand(
        idempotency_key=f" {'k' * 255} ",
        notification_type="event",
        title="title",
        text="text",
        recipient_user_ids=(uuid4(),),
    )

    result = CreateNotificationUseCase(repository).execute(command)

    assert result.idempotency_key == "k" * 255


@pytest.mark.parametrize("idempotency_key", ["   ", "k" * 256])
def test_create_notification_rejects_empty_or_oversized_key(idempotency_key):
    repository = FakeNotificationRepository()
    command = CreateNotificationCommand(
        idempotency_key=idempotency_key,
        notification_type="event",
        title="title",
        text="text",
        recipient_user_ids=(uuid4(),),
    )

    with pytest.raises(NotificationValidationError):
        CreateNotificationUseCase(repository).execute(command)

    assert repository.created is None


def test_mark_viewed_uses_current_user_and_browser_as_identity():
    repository = FakeNotificationRepository()
    notification_id, user_id, browser_id = uuid4(), uuid4(), uuid4()

    result = MarkNotificationViewedUseCase(repository).execute(
        notification_id, user_id, browser_id
    )

    assert result is None
    assert repository.marked == (notification_id, user_id, browser_id)


def test_read_use_cases_pass_current_user_and_validate_pagination():
    from app.domain.notifications import NotificationQueryValidationError
    from app.use_cases.notifications import (
        CountUnviewedNotificationsUseCase,
        GetOwnNotificationUseCase,
        ListNotificationHistoryUseCase,
        ListUnviewedNotificationsUseCase,
    )

    repository = FakeNotificationRepository()
    user_id, notification_id = uuid4(), uuid4()
    history = ListNotificationHistoryUseCase(repository)
    unviewed = ListUnviewedNotificationsUseCase(repository)
    count = CountUnviewedNotificationsUseCase(repository)
    get_own = GetOwnNotificationUseCase(repository)

    assert history.execute(user_id, offset=5, limit=10) == []
    assert unviewed.execute(user_id, offset=2, limit=8) == []
    assert count.execute(user_id) == 0
    assert get_own.execute(notification_id, user_id) is None
    assert repository.read_calls == [
        ("history", user_id, 5, 10),
        ("unviewed", user_id, 2, 8),
        ("count", user_id),
        ("get", notification_id, user_id),
    ]
    with pytest.raises(NotificationQueryValidationError):
        history.execute(user_id, offset=-1)
    with pytest.raises(NotificationQueryValidationError):
        unviewed.execute(user_id, limit=101)
