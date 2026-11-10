from typing import cast
from uuid import uuid4

from app.domain.notifications import NotificationView
from app.web.notifications.schemas import (
    AdminNotificationItemSchema,
    NotificationItemSchema,
    NotificationListQuerySchema,
)


def test_user_notification_response_omits_browser_and_admin_schema_exposes_metadata():
    item = NotificationView(
        notification_id=uuid4(),
        notification_type="shift.completed",
        title="Completed",
        text="Shift completed",
        created_at=1793600000123,
        notification_recipient_id=uuid4(),
        user_id=uuid4(),
        viewed=True,
        viewed_at=1793600000456,
        browser_id=uuid4(),
    )

    user_data = cast(
        dict[str, object], cast(object, NotificationItemSchema().dump(item))
    )
    admin_data = cast(
        dict[str, object], cast(object, AdminNotificationItemSchema().dump(item))
    )

    assert "browser_id" not in user_data
    assert "user_id" not in user_data
    assert user_data.get("notification_id") == str(item.notification_id)
    assert user_data.get("created_at") == 1793600000123
    assert admin_data.get("browser_id") == str(item.browser_id)
    assert admin_data.get("notification_recipient_id") == str(
        item.notification_recipient_id
    )


def test_notification_list_query_validates_offset_and_limit():
    schema = NotificationListQuerySchema()

    assert schema.load({}) == {"offset": 0, "limit": 50}
    assert schema.load({"offset": "5", "limit": "10"}) == {
        "offset": 5,
        "limit": 10,
    }
