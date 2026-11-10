from sqlalchemy import or_, select, text, update

from app.database import db_globals
from app.database.models.push_subscriptions import PushSubscriptions
from app.database.models.auth_sessions import AuthSessions
from app.domain.push_subscriptions import PushSubscription


class SQLAlchemyPushSubscriptionRepository:
    @staticmethod
    def _factory():
        if db_globals.Session is None:
            raise RuntimeError("Database session is not initialized")
        return db_globals.Session

    @staticmethod
    def _entity(row):
        return PushSubscription(**{name: getattr(row, name) for name in PushSubscription.__dataclass_fields__})

    def list_for_user(self, user_id, offset, limit):
        with self._factory()() as session:
            rows = session.scalars(select(PushSubscriptions).where(
                PushSubscriptions.user_id == user_id,
            ).order_by(PushSubscriptions.created_at.desc(),
                       PushSubscriptions.subscription_id.desc()).offset(offset).limit(limit))
            return [self._entity(row) for row in rows]

    def register(self, subscription):
        with self._factory()() as session, session.begin():
            # Keep the common order with logout/refresh: auth-session row,
            # then push advisory locks.  This closes the JWT-validation/write
            # race without treating browser_id as an authentication factor.
            auth_session = session.execute(select(AuthSessions).where(
                AuthSessions.session_id == subscription.auth_session_id,
                AuthSessions.user_id == subscription.user_id,
            ).with_for_update()).scalar_one_or_none()
            if (
                auth_session is None
                or auth_session.revoked_at is not None
                or auth_session.browser_id != subscription.browser_id
            ):
                raise PermissionError("Authorization session is invalid")
            # Serialize registration transfers, including cross-device token swaps.
            session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": "push:registration"})
            # Lock identities even when their rows do not yet exist.
            keys = sorted(("browser:" + str(subscription.browser_id), "token:" + subscription.token))
            for key in keys:
                session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": "push:" + key})
            session.execute(update(PushSubscriptions).where(
                PushSubscriptions.active.is_(True),
                or_(PushSubscriptions.browser_id == subscription.browser_id, PushSubscriptions.token == subscription.token),
                ~((PushSubscriptions.user_id == subscription.user_id) & (PushSubscriptions.browser_id == subscription.browser_id)),
            ).values(active=False, revoked_at=subscription.updated_at, updated_at=subscription.updated_at))
            row = session.execute(select(PushSubscriptions).where(
                PushSubscriptions.user_id == subscription.user_id,
                PushSubscriptions.browser_id == subscription.browser_id,
            ).with_for_update()).scalar_one_or_none()
            if row is None:
                row = PushSubscriptions(**{name: getattr(subscription, name) for name in PushSubscription.__dataclass_fields__})
                session.add(row)
            else:
                row.token = subscription.token
                row.platform = subscription.platform
                row.auth_session_id = subscription.auth_session_id
                row.active = True
                row.revoked_at = None
                row.updated_at = subscription.updated_at
            session.flush()
            return self._entity(row)

    def revoke(self, subscription_id, user_id, now):
        with self._factory()() as session, session.begin():
            row = session.execute(select(PushSubscriptions).where(
                PushSubscriptions.subscription_id == subscription_id,
                PushSubscriptions.user_id == user_id,
            ).with_for_update()).scalar_one_or_none()
            if row is None:
                return None
            if row.active:
                row.active = False
                row.revoked_at = now
                row.updated_at = now
                session.flush()
            return self._entity(row)
