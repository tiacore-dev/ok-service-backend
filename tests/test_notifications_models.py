from app.database.db_setup import Base
from app.database.models.notifications import NotificationRecipients, Notifications
from app.database.models.push_deliveries import PushDeliveries


def test_notifications_tables_are_registered_with_expected_columns_and_constraints():
    assert Notifications.__tablename__ == "notifications"
    assert {
        "notification_type",
        "title",
        "text",
        "created_at",
        "created_by",
        "link",
        "related_entity_type",
        "related_entity_id",
        "idempotency_key",
    }.issubset(Notifications.__table__.c.keys())
    assert NotificationRecipients.__tablename__ == "notification_recipients"
    assert {
        "notification_id",
        "user_id",
        "viewed",
        "viewed_at",
        "browser_id",
    }.issubset(NotificationRecipients.__table__.c.keys())
    assert any(
        constraint.name == "uq_notification_recipients_notification_user"
        for constraint in NotificationRecipients.__table__.constraints
    )
    assert any(
        constraint.name == "uq_notifications_idempotency_key"
        for constraint in Notifications.__table__.constraints
    )
    assert "notifications" in Base.metadata.tables
    assert "notification_recipients" in Base.metadata.tables


def test_push_delivery_queue_has_per_recipient_subscription_deduplication():
    assert PushDeliveries.__tablename__ == "push_deliveries"
    assert {
        "notification_recipient_id", "subscription_id", "status", "attempts",
        "next_attempt_at", "locked_until", "locked_by", "lease_token", "sent_at",
        "provider_message_id", "last_error",
    }.issubset(PushDeliveries.__table__.c.keys())
    assert any(
        constraint.name == "uq_push_deliveries_recipient_subscription"
        for constraint in PushDeliveries.__table__.constraints
    )


def test_view_metadata_constraints_require_timestamp_and_keep_unviewed_empty():
    constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in NotificationRecipients.__table__.constraints
        if hasattr(constraint, "sqltext")
    }
    assert (
        "NOT viewed OR (viewed_at IS NOT NULL AND browser_id IS NOT NULL)"
        == constraints["ck_notification_recipients_view_metadata"]
    )
    assert "viewed OR (viewed_at IS NULL AND browser_id IS NULL)" == constraints[
        "ck_notification_recipients_unviewed_metadata"
    ]
