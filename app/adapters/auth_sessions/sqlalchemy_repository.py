from __future__ import annotations

from typing import Callable
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import db_globals
from app.database.models.auth_sessions import AuthSessions, RefreshTokens
from app.domain.auth_sessions import AuthSession, RefreshToken


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
        if token.session_id != session.session_id or token.jti != session.current_token_jti:
            raise ValueError("Initial refresh token does not match the session state")

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

    def revoke_session(self, session_id: UUID, revoked_at: int) -> bool:
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
