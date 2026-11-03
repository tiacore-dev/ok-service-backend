from dataclasses import dataclass, replace
from uuid import UUID, uuid4

import pytest
from marshmallow import ValidationError

from app.domain.notifications import NotificationValidationError
from app.use_cases.notifications.bulk import BulkNotificationUseCase
from app.web.notifications.schemas import BulkNotificationSchema


class Repository:
    def create_notification(self, notification, recipient_user_ids):
        self.recipients = recipient_user_ids
        return notification


@dataclass(frozen=True)
class BulkArguments:
    actor_id: UUID
    recipients: tuple[UUID, ...]
    title: str
    text: str
    link: str | None
    key: str


def test_bulk_scopes_key_to_sender_and_preserves_recipients():
    repo = Repository()
    actor, recipient = uuid4(), uuid4()
    use_case = BulkNotificationUseCase(repo)
    first = use_case.execute(actor, (recipient,), "Title", "Text", "/path", "key")
    repeat = use_case.execute(actor, (recipient,), "Title", "Text", "/path", "key")
    other = use_case.execute(uuid4(), (recipient,), "Title", "Text", "/path", "key")
    assert first.idempotency_key == repeat.idempotency_key != other.idempotency_key
    assert first.created_by == actor and repo.recipients == (recipient,)


@pytest.mark.parametrize("field,value", [
    ("recipients", ()), ("recipients", (uuid4(),) * 2),
    ("title", " "), ("text", " "), ("text", "x" * 4001),
    ("key", "bad key"), ("link", "//evil.example"),
    ("link", "/%2fexample"), ("link", "/%252fexample"),
    ("link", "/\\evil"), ("link", "https://example.com"),
])
def test_bulk_rejects_invalid_input(field, value):
    data = replace(BulkArguments(uuid4(), (uuid4(),), "Title", "Text", None, "key"), **{field: value})
    with pytest.raises(NotificationValidationError):
        BulkNotificationUseCase(Repository()).execute(
            data.actor_id, data.recipients, data.title, data.text, data.link, data.key
        )


def test_bulk_schema_rejects_bad_uuid_and_unknown_fields():
    schema = BulkNotificationSchema()
    with pytest.raises(ValidationError):
        schema.load(dict(recipient_user_ids=["bad"], title="a", text="b", idempotency_key="k"))
    with pytest.raises(ValidationError):
        schema.load(dict(recipient_user_ids=[str(uuid4())], title="a", text="b", idempotency_key="k", role="admin"))
