from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID as UUIDValue, uuid4

from sqlalchemy import BigInteger, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_milliseconds

if TYPE_CHECKING:
    from app.database.models.user import Users


class AuthSessions(Base):
    """Server-side authorization session; JWT values are deliberately never stored."""

    __tablename__ = "auth_sessions"

    session_id: Mapped[UUIDValue] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUIDValue] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=utc_epoch_milliseconds,
        server_default=text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
    )
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    revoked_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_token_jti: Mapped[UUIDValue] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True
    )
    browser_id: Mapped[UUIDValue | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    user: Mapped[Users] = relationship("Users")
    refresh_tokens: Mapped[list[RefreshTokens]] = relationship(
        "RefreshTokens", back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_auth_sessions_user_revoked", "user_id", "revoked_at"),
    )


class RefreshTokens(Base):
    """Refresh-token lineage keyed by Flask-JWT-Extended's UUID ``jti`` claim."""

    __tablename__ = "refresh_tokens"

    jti: Mapped[UUIDValue] = mapped_column(UUID(as_uuid=True), primary_key=True)
    session_id: Mapped[UUIDValue] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=utc_epoch_milliseconds,
        server_default=text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
    )
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    used_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    revoked_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    replaced_by_jti: Mapped[UUIDValue | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    session: Mapped[AuthSessions] = relationship(
        "AuthSessions", back_populates="refresh_tokens"
    )

    __table_args__ = (
        Index("ix_refresh_tokens_session_state", "session_id", "used_at", "revoked_at"),
    )
