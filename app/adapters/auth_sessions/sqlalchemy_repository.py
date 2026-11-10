from __future__ import annotations

from typing import Callable
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.database import db_globals
from app.database.models.auth_sessions import AuthSessions, RefreshTokens
from app.database.models.push_subscriptions import PushSubscriptions
from app.domain.auth_sessions import AuthSession, RefreshToken

ROTATED = "rotated"
REUSED = "reused"
INACTIVE = "inactive"


class SQLAlchemyAuthSessionRepository:
    """PostgreSQL-backed server session storage.

    The rotation primitive locks the session before the refresh-token row. All
    future writers must preserve that order to avoid deadlocks.
    """

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory

    def _new_session(self) -> Session:
        factory = self._session_factory or db_globals.Session
        if factory is None:
            raise RuntimeError("Database session is not initialized")
        # Test configuration uses scoped_session.  Session lifecycle for auth
        # rotation must be independent from an ambient web/test transaction,
        # otherwise ``begin()`` can accidentally nest into the caller's unit
        # of work.  Production sessionmaker has no ``session_factory``.
        scoped_factory = getattr(factory, "session_factory", None)
        if scoped_factory is not None:
            return scoped_factory()
        return factory()

    @staticmethod
    def _session_entity(record: AuthSessions) -> AuthSession:
        return AuthSession(
            session_id=record.session_id,
            user_id=record.user_id,
            created_at=record.created_at,
            expires_at=record.expires_at,
            current_token_jti=record.current_token_jti,
            revoked_at=record.revoked_at,
            browser_id=record.browser_id,
        )

    @staticmethod
    def _token_entity(record: RefreshTokens) -> RefreshToken:
        return RefreshToken(
            jti=record.jti,
            session_id=record.session_id,
            created_at=record.created_at,
            expires_at=record.expires_at,
            used_at=record.used_at,
            revoked_at=record.revoked_at,
            replaced_by_jti=record.replaced_by_jti,
        )

    def create_session(self, session: AuthSession) -> AuthSession:
        db_session = self._new_session()
        try:
            with db_session.begin():
                record = AuthSessions(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    created_at=session.created_at,
                    expires_at=session.expires_at,
                    current_token_jti=session.current_token_jti,
                    revoked_at=session.revoked_at,
                    browser_id=session.browser_id,
                )
                db_session.add(record)
                db_session.flush()
                return self._session_entity(record)
        finally:
            db_session.close()

    def save_refresh_token(self, token: RefreshToken) -> RefreshToken:
        db_session = self._new_session()
        try:
            with db_session.begin():
                record = RefreshTokens(
                    jti=token.jti,
                    session_id=token.session_id,
                    created_at=token.created_at,
                    expires_at=token.expires_at,
                    used_at=token.used_at,
                    revoked_at=token.revoked_at,
                    replaced_by_jti=token.replaced_by_jti,
                )
                db_session.add(record)
                db_session.flush()
                return self._token_entity(record)
        finally:
            db_session.close()

    def create_session_with_refresh_token(
        self, session: AuthSession, token: RefreshToken
    ) -> AuthSession:
        if (
            token.session_id != session.session_id
            or token.jti != session.current_token_jti
        ):
            raise ValueError("Initial refresh token does not match the session state")

        db_session = self._new_session()
        try:
            with db_session.begin():
                # Login has no existing session row to lock yet.  Serialize
                # browser-local session replacement before looking up prior
                # sessions, otherwise two concurrent logins can both observe
                # an empty set and commit two active sessions.
                if session.browser_id is not None:
                    self._lock_auth_browser_login(db_session, session.browser_id)
                record = AuthSessions(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    created_at=session.created_at,
                    expires_at=session.expires_at,
                    current_token_jti=session.current_token_jti,
                    revoked_at=session.revoked_at,
                    browser_id=session.browser_id,
                )
                db_session.add(record)
                db_session.add(
                    RefreshTokens(
                        jti=token.jti,
                        session_id=token.session_id,
                        created_at=token.created_at,
                        expires_at=token.expires_at,
                        used_at=token.used_at,
                        revoked_at=token.revoked_at,
                        replaced_by_jti=token.replaced_by_jti,
                    )
                )
                # A successful login starts a new browser-local authorization
                # context.  Any prior subscription on that browser (including
                # another user) is revoked in the same transaction.  A failed
                # session insert therefore cannot leave a partial transfer.
                if session.browser_id is not None:
                    # A browser-local account switch invalidates sessions that
                    # were created for that same browser.  Otherwise a still
                    # valid access JWT of user A could immediately register a
                    # new active push subscription after user B logs in.
                    previous_session_ids = list(
                        db_session.scalars(
                            select(AuthSessions.session_id)
                            .where(
                                AuthSessions.browser_id == session.browser_id,
                                AuthSessions.session_id != session.session_id,
                                AuthSessions.revoked_at.is_(None),
                            )
                            .order_by(AuthSessions.session_id)
                            .with_for_update()
                        )
                    )
                    if previous_session_ids:
                        db_session.execute(
                            update(AuthSessions)
                            .where(AuthSessions.session_id.in_(previous_session_ids))
                            .values(revoked_at=session.created_at)
                        )
                        db_session.execute(
                            update(RefreshTokens)
                            .where(
                                RefreshTokens.session_id.in_(previous_session_ids),
                                RefreshTokens.revoked_at.is_(None),
                            )
                            .values(revoked_at=session.created_at)
                        )
                    self._lock_push_browser(db_session, session.browser_id)
                    db_session.execute(
                        update(PushSubscriptions)
                        .where(
                            PushSubscriptions.browser_id == session.browser_id,
                            PushSubscriptions.active.is_(True),
                        )
                        .values(
                            active=False,
                            revoked_at=session.created_at,
                            updated_at=session.created_at,
                        )
                    )
                db_session.flush()
                return self._session_entity(record)
        finally:
            db_session.close()

    def get_session(self, session_id: UUID) -> AuthSession | None:
        db_session = self._new_session()
        try:
            record = db_session.get(AuthSessions, session_id)
            return self._session_entity(record) if record is not None else None
        finally:
            db_session.close()

    def get_refresh_token(self, jti: UUID) -> RefreshToken | None:
        db_session = self._new_session()
        try:
            record = db_session.get(RefreshTokens, jti)
            return self._token_entity(record) if record is not None else None
        finally:
            db_session.close()

    def replace_current_refresh_token(
        self,
        session_id: UUID,
        expected_jti: UUID,
        replacement: RefreshToken,
        now: int,
    ) -> bool:
        if replacement.session_id != session_id:
            raise ValueError("Replacement refresh token belongs to another session")

        db_session = self._new_session()
        try:
            with db_session.begin():
                session = db_session.scalar(
                    select(AuthSessions)
                    .where(AuthSessions.session_id == session_id)
                    .with_for_update()
                )
                if (
                    session is None
                    or session.revoked_at is not None
                    or session.expires_at <= now
                    or session.current_token_jti != expected_jti
                ):
                    return False

                token = db_session.scalar(
                    select(RefreshTokens)
                    .where(
                        RefreshTokens.jti == expected_jti,
                        RefreshTokens.session_id == session_id,
                    )
                    .with_for_update()
                )
                if (
                    token is None
                    or token.used_at is not None
                    or token.revoked_at is not None
                    or token.expires_at <= now
                ):
                    return False

                db_session.add(
                    RefreshTokens(
                        jti=replacement.jti,
                        session_id=replacement.session_id,
                        created_at=replacement.created_at,
                        expires_at=replacement.expires_at,
                        used_at=replacement.used_at,
                        revoked_at=replacement.revoked_at,
                        replaced_by_jti=replacement.replaced_by_jti,
                    )
                )
                token.used_at = now
                token.replaced_by_jti = replacement.jti
                session.current_token_jti = replacement.jti
                db_session.flush()
                return True
        finally:
            db_session.close()

    def rotate_refresh_token(
        self,
        session_id: UUID,
        expected_jti: UUID,
        replacement: RefreshToken,
        now: int,
    ) -> str:
        """Rotate under one transaction, revoking on a known stale token."""
        if replacement.session_id != session_id:
            raise ValueError("Replacement refresh token belongs to another session")

        db_session = self._new_session()
        try:
            with db_session.begin():
                session = db_session.scalar(
                    select(AuthSessions)
                    .where(AuthSessions.session_id == session_id)
                    .with_for_update()
                )
                if (
                    session is None
                    or session.revoked_at is not None
                    or session.expires_at <= now
                ):
                    return INACTIVE

                token = db_session.scalar(
                    select(RefreshTokens)
                    .where(
                        RefreshTokens.jti == expected_jti,
                        RefreshTokens.session_id == session_id,
                    )
                    .with_for_update()
                )
                if (
                    token is None
                    or session.current_token_jti != expected_jti
                    or token.used_at is not None
                    or token.revoked_at is not None
                    or token.expires_at <= now
                ):
                    # The token belongs to this locked session but is stale:
                    # commit full-session revocation before returning an error.
                    session.revoked_at = now
                    db_session.execute(
                        update(RefreshTokens)
                        .where(
                            RefreshTokens.session_id == session_id,
                            RefreshTokens.revoked_at.is_(None),
                        )
                        .values(revoked_at=now)
                    )
                    self._revoke_bound_push_subscription(db_session, session, now)
                    return REUSED

                db_session.add(
                    RefreshTokens(
                        jti=replacement.jti,
                        session_id=replacement.session_id,
                        created_at=replacement.created_at,
                        expires_at=replacement.expires_at,
                    )
                )
                token.used_at = now
                token.replaced_by_jti = replacement.jti
                session.current_token_jti = replacement.jti
                session.expires_at = max(session.expires_at, replacement.expires_at)
                db_session.flush()
                return ROTATED
        finally:
            db_session.close()

    @staticmethod
    def _lock_auth_browser_login(session: Session, browser_id: UUID) -> None:
        """Serialize login's read/revoke/write sequence for one browser."""
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": "auth:browser:" + str(browser_id)},
        )

    @staticmethod
    def _lock_push_browser(session: Session, browser_id: UUID) -> None:
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": "push:registration"},
        )
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": "push:browser:" + str(browser_id)},
        )

    def _revoke_bound_push_subscription(
        self, db_session: Session, session: AuthSessions, revoked_at: int
    ) -> None:
        """Deactivate the subscription proven by the locked auth session."""
        if session.browser_id is None:
            return
        # Keep the shared order used by registration: session row first, then
        # push advisory locks.  The browser is used only as the lock key; the
        # persisted session association, not a request cookie, selects rows.
        self._lock_push_browser(db_session, session.browser_id)
        db_session.execute(
            update(PushSubscriptions)
            .where(
                PushSubscriptions.user_id == session.user_id,
                PushSubscriptions.auth_session_id == session.session_id,
                PushSubscriptions.active.is_(True),
            )
            .values(
                active=False,
                revoked_at=revoked_at,
                updated_at=revoked_at,
            )
        )

    def revoke_session(
        self,
        session_id: UUID,
        user_id: UUID,
        revoked_at: int,
    ) -> bool:
        db_session = self._new_session()
        try:
            with db_session.begin():
                session = db_session.scalar(
                    select(AuthSessions)
                    .where(AuthSessions.session_id == session_id)
                    .with_for_update()
                )
                if session is None:
                    return False
                if session.user_id != user_id:
                    return False
                if session.revoked_at is None:
                    session.revoked_at = revoked_at
                db_session.execute(
                    update(RefreshTokens)
                    .where(
                        RefreshTokens.session_id == session_id,
                        RefreshTokens.revoked_at.is_(None),
                    )
                    .values(revoked_at=revoked_at)
                )
                self._revoke_bound_push_subscription(db_session, session, revoked_at)
                return True
        finally:
            db_session.close()

    def is_session_active(self, session_id: UUID, user_id: UUID, now: int) -> bool:
        db_session = self._new_session()
        try:
            return bool(
                db_session.scalar(
                    select(AuthSessions.session_id).where(
                        AuthSessions.session_id == session_id,
                        AuthSessions.user_id == user_id,
                        AuthSessions.revoked_at.is_(None),
                        AuthSessions.expires_at > now,
                    )
                )
            )
        finally:
            db_session.close()
