from typing import Protocol
from uuid import UUID

from app.domain.auth_sessions import AuthSession, RefreshToken


class AuthSessionRepository(Protocol):
    def create_session(self, session: AuthSession) -> AuthSession: ...

    def save_refresh_token(self, token: RefreshToken) -> RefreshToken: ...

    def create_session_with_refresh_token(
        self, session: AuthSession, token: RefreshToken
    ) -> AuthSession:
        """Persist an initial session and its current refresh token atomically."""
        ...

    def get_session(self, session_id: UUID) -> AuthSession | None: ...

    def get_refresh_token(self, jti: UUID) -> RefreshToken | None: ...

    def replace_current_refresh_token(
        self,
        session_id: UUID,
        expected_jti: UUID,
        replacement: RefreshToken,
        now: int,
    ) -> bool:
        """Atomically consume ``expected_jti`` and install ``replacement``."""
        ...

    def revoke_session(self, session_id: UUID, revoked_at: int) -> bool: ...

    def is_session_active(self, session_id: UUID, user_id: UUID, now: int) -> bool: ...
