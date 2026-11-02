from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthSession:
    session_id: UUID
    user_id: UUID
    created_at: int
    expires_at: int
    current_token_jti: UUID
    revoked_at: int | None = None


@dataclass(frozen=True, slots=True)
class RefreshToken:
    jti: UUID
    session_id: UUID
    created_at: int
    expires_at: int
    used_at: int | None = None
    revoked_at: int | None = None
    replaced_by_jti: UUID | None = None
