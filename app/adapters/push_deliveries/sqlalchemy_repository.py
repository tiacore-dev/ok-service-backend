from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sqlalchemy import and_, literal_column, or_, select, update

from app.database import db_globals
from app.database.models.auth_sessions import AuthSessions
from app.database.models.notifications import NotificationRecipients, Notifications
from app.database.models.push_deliveries import PushDeliveries
from app.database.models.push_subscriptions import PushSubscriptions
from app.database.models.user import Users
from app.database.time_utils import utc_epoch_milliseconds
from app.domain.push_notifications import PushDeliveryStatus

_PG_CLOCK_MS = literal_column("CAST(EXTRACT(EPOCH FROM clock_timestamp()) * 1000 AS BIGINT)")


@dataclass(frozen=True, slots=True)
class ClaimedPushDelivery:
    delivery_id: UUID
    notification_id: UUID
    subscription_id: UUID
    token: str = field(repr=False)
    title: str
    body: str
    route: str
    lease_token: UUID
    attempts: int
    auth_session_id: UUID | None = None


class SQLAlchemyPushDeliveryRepository:
    """PostgreSQL queue adapter; every state transition checks its lease token."""

    @staticmethod
    def _factory():
        if db_globals.Session is None:
            raise RuntimeError("Database session is not initialized")
        return db_globals.Session

    def claim_ready(
        self, worker_id: str, batch_size: int, lease_ms: int, max_attempts: int
    ) -> list[ClaimedPushDelivery]:
        if batch_size < 1 or lease_ms < 1 or max_attempts < 1:
            raise ValueError("batch_size, lease_ms and max_attempts must be positive")
        factory = self._factory()
        with factory() as session, session.begin():
            now = session.scalar(select(_PG_CLOCK_MS))
            # An already-expired final attempt cannot remain processing forever.
            session.execute(
                update(PushDeliveries)
                .where(
                    PushDeliveries.status == "processing",
                    PushDeliveries.locked_until <= now,
                    PushDeliveries.attempts >= max_attempts,
                )
                .values(
                    status="failed", locked_until=None, locked_by=None,
                    lease_token=None, last_error="attempt_limit_exceeded", updated_at=now,
                )
            )
            candidate_ids = session.scalars(
                select(PushDeliveries.delivery_id)
                .where(
                    PushDeliveries.attempts < max_attempts,
                    or_(
                        and_(
                            PushDeliveries.status.in_(("pending", "retry")),
                            PushDeliveries.next_attempt_at <= now,
                        ),
                        and_(
                            PushDeliveries.status == "processing",
                            PushDeliveries.locked_until <= now,
                        ),
                    ),
                )
                .order_by(PushDeliveries.next_attempt_at, PushDeliveries.delivery_id)
                .with_for_update(skip_locked=True)
                .limit(batch_size)
            ).all()
            if not candidate_ids:
                return []
            lease_token = uuid4()
            session.execute(
                update(PushDeliveries)
                .where(PushDeliveries.delivery_id.in_(candidate_ids))
                .values(
                    status="processing", attempts=PushDeliveries.attempts + 1,
                    locked_until=_PG_CLOCK_MS + lease_ms, locked_by=worker_id,
                    lease_token=lease_token, updated_at=now,
                )
            )
            rows = session.execute(
                select(PushDeliveries, Notifications, PushSubscriptions)
                .join(
                    NotificationRecipients,
                    NotificationRecipients.notification_recipient_id
                    == PushDeliveries.notification_recipient_id,
                )
                .join(
                    Notifications,
                    Notifications.notification_id == NotificationRecipients.notification_id,
                )
                .join(
                    PushSubscriptions,
                    PushSubscriptions.subscription_id == PushDeliveries.subscription_id,
                )
                .where(PushDeliveries.delivery_id.in_(candidate_ids))
            ).all()
            return [
                ClaimedPushDelivery(
                    delivery_id=delivery.delivery_id,
                    notification_id=notification.notification_id,
                    subscription_id=subscription.subscription_id,
                    token=subscription.token,
                    title=notification.title,
                    body=notification.text,
                    route=notification.link or f"/notifications/{notification.notification_id}",
                    lease_token=lease_token,
                    attempts=delivery.attempts,
                    auth_session_id=subscription.auth_session_id,
                )
                for delivery, notification, subscription in rows
            ]

    def is_eligible(self, delivery: ClaimedPushDelivery) -> bool:
        """Check the current recipient, device, session and lease in one snapshot."""
        factory = self._factory()
        with factory() as session:
            return (
                session.execute(
                    select(PushDeliveries.delivery_id)
                    .join(
                        NotificationRecipients,
                        NotificationRecipients.notification_recipient_id
                        == PushDeliveries.notification_recipient_id,
                    )
                    .join(Users, Users.user_id == NotificationRecipients.user_id)
                    .join(
                        PushSubscriptions,
                        PushSubscriptions.subscription_id == PushDeliveries.subscription_id,
                    )
                    .join(
                        AuthSessions,
                        AuthSessions.session_id == PushSubscriptions.auth_session_id,
                    )
                    .where(
                        PushDeliveries.delivery_id == delivery.delivery_id,
                        PushDeliveries.status == "processing",
                        PushDeliveries.lease_token == delivery.lease_token,
                        PushDeliveries.locked_until > _PG_CLOCK_MS,
                        PushSubscriptions.active.is_(True),
                        PushSubscriptions.user_id == NotificationRecipients.user_id,
                        PushSubscriptions.auth_session_id == delivery.auth_session_id,
                        PushSubscriptions.token == delivery.token,
                        Users.is_active.is_(True),
                        Users.deleted.is_(False),
                        AuthSessions.revoked_at.is_(None),
                        AuthSessions.user_id == PushSubscriptions.user_id,
                        AuthSessions.expires_at > _PG_CLOCK_MS,
                    )
                ).scalar_one_or_none()
                is not None
            )

    def mark_ineligible(self, delivery: ClaimedPushDelivery) -> bool:
        return self._finish(
            delivery, "failed", error="recipient_or_subscription_ineligible"
        )

    def record_result(
        self,
        delivery: ClaimedPushDelivery,
        result: PushDeliveryStatus,
        *,
        provider_message_id: str | None = None,
        error_code: str | None = None,
        max_attempts: int,
        retry_delay_ms: int,
    ) -> bool:
        if result is PushDeliveryStatus.SENT:
            return self._finish(
                delivery, "sent", provider_message_id=provider_message_id
            )
        if result is PushDeliveryStatus.INVALID_TOKEN:
            return self._finish(
                delivery, "failed", error=error_code or "invalid_token", revoke=True
            )
        # Disabled/no Firebase configuration is diagnosable and retryable, but it
        # never revokes a device.  It reaches failed after the configured limit.
        target = "retry" if delivery.attempts < max_attempts else "failed"
        return self._finish(
            delivery,
            target,
            error=error_code or result.value,
            next_attempt_at=utc_epoch_milliseconds() + retry_delay_ms
            if target == "retry"
            else None,
        )

    def _finish(
        self,
        delivery: ClaimedPushDelivery,
        status: str,
        *,
        provider_message_id: str | None = None,
        error: str | None = None,
        next_attempt_at: int | None = None,
        revoke: bool = False,
    ) -> bool:
        now = utc_epoch_milliseconds()
        factory = self._factory()
        with factory() as session, session.begin():
            # Lock first: the lease must still be valid after any lock wait.
            session.execute(
                select(PushDeliveries.delivery_id)
                .where(PushDeliveries.delivery_id == delivery.delivery_id)
                .with_for_update()
            ).scalar_one_or_none()
            values = {
                "status": status,
                "locked_until": None,
                "locked_by": None,
                "lease_token": None,
                "updated_at": now,
                "last_error": (error or "")[:512] or None,
                "provider_message_id": (provider_message_id or "")[:512] or None,
            }
            if status == "sent":
                values["sent_at"] = now
            if next_attempt_at is not None:
                values["next_attempt_at"] = next_attempt_at
            updated = session.execute(
                update(PushDeliveries)
                .where(
                    PushDeliveries.delivery_id == delivery.delivery_id,
                    PushDeliveries.status == "processing",
                    PushDeliveries.lease_token == delivery.lease_token,
                    PushDeliveries.locked_until > _PG_CLOCK_MS,
                )
                .values(**values)
                .returning(PushDeliveries.delivery_id)
            ).scalar_one_or_none()
            # A stale worker cannot revoke a device: first prove that it still
            # owns this lease, then change the subscription in the same local
            # transaction as the terminal delivery state.
            if updated is not None and revoke:
                session.execute(
                    update(PushSubscriptions)
                    .where(
                        PushSubscriptions.subscription_id == delivery.subscription_id,
                        PushSubscriptions.active.is_(True),
                        PushSubscriptions.token == delivery.token,
                        PushSubscriptions.auth_session_id == delivery.auth_session_id,
                    )
                    .values(active=False, revoked_at=now, updated_at=now)
                )
            return updated is not None
