"""Flask-JWT-Extended callbacks for server-bound authorization sessions."""

from __future__ import annotations

import json
import logging
from uuid import UUID

from flask import Flask, g
from flask_jwt_extended import JWTManager

from app.adapters.auth_sessions import SQLAlchemyAuthSessionRepository
from app.database import db_globals
from app.database.models import Users
from app.database.time_utils import utc_epoch_milliseconds

logger = logging.getLogger("ok_service")


class JWTSessionUnavailable(RuntimeError):
    """The server cannot determine whether a JWT session is still active."""


def _identity_user_id(payload: dict) -> UUID | None:
    identity = payload.get("sub")
    try:
        data = json.loads(identity) if isinstance(identity, str) else identity
        return UUID(str(data["user_id"])) if isinstance(data, dict) else None
    except (KeyError, TypeError, ValueError):
        return None


def _session_id(payload: dict) -> UUID | None:
    try:
        return UUID(str(payload["session_id"]))
    except (KeyError, TypeError, ValueError):
        return None


def _active_user(user_id: UUID) -> dict | None:
    factory = db_globals.Session
    if factory is None:
        raise RuntimeError("Database session is not initialized")
    scoped_factory = getattr(factory, "session_factory", None)
    session = scoped_factory() if scoped_factory is not None else factory()
    try:
        user = session.get(Users, user_id)
        if user is None or user.deleted or not user.is_active:
            return None
        return user.to_dict()
    finally:
        session.close()


def _is_active(payload: dict) -> bool:
    session_id = _session_id(payload)
    user_id = _identity_user_id(payload)
    if session_id is None or user_id is None:
        return False
    try:
        return SQLAlchemyAuthSessionRepository().is_session_active(
            session_id, user_id, utc_epoch_milliseconds()
        )
    except Exception as error:
        logger.exception("JWT session verification failed")
        raise JWTSessionUnavailable("JWT session verification is unavailable") from error


def configure_jwt_callbacks(app: Flask, jwt: JWTManager) -> None:
    """Install fail-closed validation and close every callback DB session."""

    @app.errorhandler(JWTSessionUnavailable)
    def jwt_session_unavailable(_error: JWTSessionUnavailable):
        return {"msg": "Authentication unavailable"}, 503

    @jwt.token_in_blocklist_loader
    def token_in_blocklist(_header: dict, payload: dict) -> bool:
        # A consumed refresh reaches /auth/refresh so that confirmed reuse can
        # revoke the whole session under the repository's row locks.
        return payload.get("type") != "refresh" and not _is_active(payload)

    @jwt.token_verification_loader
    def token_verification(_header: dict, payload: dict) -> bool:
        if not _is_active(payload):
            return False
        user_id = _identity_user_id(payload)
        if user_id is None:
            return False
        try:
            user = _active_user(user_id)
        except Exception as error:
            logger.exception("JWT user verification failed")
            raise JWTSessionUnavailable("JWT user verification is unavailable") from error
        if user is None:
            return False
        g.jwt_current_user = user
        return True

    @jwt.token_verification_failed_loader
    def verification_failed(_header: dict, _payload: dict):
        return {"msg": "JWT session is invalid"}, 401

    @jwt.revoked_token_loader
    def revoked_token(_header: dict, _payload: dict):
        return {"msg": "JWT session is invalid"}, 401
