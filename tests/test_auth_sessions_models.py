from uuid import uuid4

from app.database.db_setup import Base
from app.database.models import AuthSessions, RefreshTokens
from app.domain.auth_sessions import AuthSession, RefreshToken


def test_auth_session_models_are_registered_with_required_constraints():
    assert AuthSessions.__tablename__ == "auth_sessions"
    assert RefreshTokens.__tablename__ == "refresh_tokens"
    assert {
        "session_id",
        "user_id",
        "created_at",
        "expires_at",
        "revoked_at",
        "current_token_jti",
    }.issubset(AuthSessions.__table__.c.keys())
    assert {
        "jti",
        "session_id",
        "created_at",
        "expires_at",
        "used_at",
        "revoked_at",
        "replaced_by_jti",
    }.issubset(RefreshTokens.__table__.c.keys())
    assert AuthSessions.__table__.c.current_token_jti.unique is True
    assert RefreshTokens.__table__.c.jti.primary_key is True
    assert "auth_sessions" in Base.metadata.tables
    assert "refresh_tokens" in Base.metadata.tables


def test_auth_session_domain_entities_keep_epoch_milliseconds_and_token_linkage():
    session_id, user_id, jti = uuid4(), uuid4(), uuid4()
    session = AuthSession(
        session_id=session_id,
        user_id=user_id,
        created_at=1_700_000_000_123,
        expires_at=1_700_000_900_123,
        current_token_jti=jti,
    )
    token = RefreshToken(
        jti=jti,
        session_id=session_id,
        created_at=session.created_at,
        expires_at=session.expires_at,
    )

    assert token.session_id == session.session_id
    assert token.created_at == session.created_at
    assert token.used_at is None and token.revoked_at is None
