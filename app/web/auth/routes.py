from __future__ import annotations

import json
import logging
from asyncio import run
from typing import TypedDict, cast
from uuid import UUID, uuid4

from flask import request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)
from flask_restx import Namespace, Resource
from marshmallow import ValidationError

from app.database.managers.user_manager import UserManager
from app.database.time_utils import utc_epoch_milliseconds
from app.adapters.auth_sessions.sqlalchemy_repository import (
    INACTIVE,
    REUSED,
    ROTATED,
    SQLAlchemyAuthSessionRepository,
)
from app.domain.auth_sessions import AuthSession, RefreshToken
from app.schemas.login_schemas import LoginSchema, RefreshTokenSchema
from app.s3.s3_manager import AsyncS3Manager
from app.web._typing import to_plain_dict
from app.web.auth.jwt_callbacks import JWTSessionUnavailable

from .models import hello_model, login_model, refresh_model, response_auth

logger = logging.getLogger("ok_service")

login_ns = Namespace("auth", description="Authentication related operations")

login_ns.models[login_model.name] = login_model
login_ns.models[refresh_model.name] = refresh_model
login_ns.models[response_auth.name] = response_auth
login_ns.models[hello_model.name] = hello_model


class LoginPayload(TypedDict):
    login: str
    password: str


class RefreshPayload(TypedDict):
    refresh_token: str


@login_ns.route("/health")
class HealthCheck(Resource):
    def get(self):
        return {"msg": "Hello, world!"}, 200


@login_ns.route("/health/s3")
class S3HealthCheck(Resource):
    @login_ns.doc(
        responses={
            200: "S3 bucket is available",
            503: "S3 bucket is unavailable",
        }
    )
    def get(self):
        if run(AsyncS3Manager().is_available()):
            return {"service": "s3", "status": "ok"}, 200
        return {"service": "s3", "status": "unavailable"}, 503


@login_ns.route("/login")
class AuthLogin(Resource):
    @login_ns.expect(login_model)
    @login_ns.marshal_with(response_auth)
    def post(self):
        db = UserManager()
        schema = LoginSchema()
        try:
            data = cast(
                LoginPayload,
                schema.load(to_plain_dict(request.json, "Request body is required")),
            )
        except ValidationError as err:
            logger.error(f"Validation error during login: {err.messages}")
            return {"error": err.messages}, 400
        except ValueError as err:
            logger.error(f"Value error during login: {err}")
            return {"msg": str(err)}, 400

        login = data["login"]
        password = data["password"]

        logger.info("Login attempt", extra={"login": login})

        user = db.authenticate(login, password)
        if user is None:
            logger.warning(
                "Authentication failed: bad username or password",
                extra={"login": login},
            )
            return {"msg": "Bad username or password"}, 401

        if user.get("deleted") is True or user.get("is_active") is not True:
            logger.warning(
                "Authentication blocked: inactive user", extra={"login": login}
            )
            return {"msg": "User is inactive"}, 401

        identity = json.dumps(
            {"user_id": user["user_id"], "role": user["role"], "login": login}
        )
        session_id = uuid4()
        # Flask-JWT-Extended owns standard jti/iat/exp claims.  Decode the token
        # it just signed to store those claims, never the raw JWT, atomically.
        refresh_token = create_refresh_token(
            identity=identity, additional_claims={"session_id": str(session_id)}
        )
        refresh_claims = decode_token(refresh_token)
        now = utc_epoch_milliseconds()
        refresh_jti = UUID(str(refresh_claims["jti"]))
        expires_at = int(refresh_claims["exp"]) * 1000
        try:
            SQLAlchemyAuthSessionRepository().create_session_with_refresh_token(
                AuthSession(
                    session_id=session_id,
                    user_id=UUID(str(user["user_id"])),
                    created_at=now,
                    expires_at=expires_at,
                    current_token_jti=refresh_jti,
                ),
                RefreshToken(
                    jti=refresh_jti,
                    session_id=session_id,
                    created_at=now,
                    expires_at=expires_at,
                ),
            )
        except Exception:
            logger.exception("Unable to create authorization session")
            return {"msg": "Authentication unavailable"}, 503

        access_token = create_access_token(
            identity=identity, additional_claims={"session_id": str(session_id)}
        )

        logger.info("Authentication successful", extra={"login": login})
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "msg": "Authentication successful",
            "user_id": user["user_id"],
        }, 200


@login_ns.route("/refresh")
class AuthRefresh(Resource):
    @login_ns.expect(refresh_model)
    @login_ns.marshal_with(response_auth)
    def post(self):
        schema = RefreshTokenSchema()
        try:
            data = cast(
                RefreshPayload,
                schema.load(to_plain_dict(request.json, "Request body is required")),
            )
        except ValidationError as err:
            logger.error(f"Validation error during refresh: {err.messages}")
            return {"error": err.messages}, 400
        except ValueError as err:
            logger.error(f"Value error during refresh: {err}")
            return {"msg": str(err)}, 400

        refresh_token = data["refresh_token"]
        logger.debug("Refresh token request received")

        if not refresh_token:
            logger.error("Missing refresh token in request")
            return {"msg": "Missing refresh token"}, 400

        try:
            verify_jwt_in_request(refresh=True, locations=["json"])
            logger.debug("Refresh token verified successfully")
        except JWTSessionUnavailable:
            return {"msg": "Authentication unavailable"}, 503
        except Exception as error:
            logger.error(
                "Refresh token verification failed",
                extra={"error_type": type(error).__name__},
            )
            return {"msg": str(error)}, 401

        claims = get_jwt()
        try:
            session_id = UUID(str(claims["session_id"]))
            old_jti = UUID(str(claims["jti"]))
            current_user = get_jwt_identity()
            user_data = json.loads(current_user) if isinstance(current_user, str) else current_user
            user_id = UUID(str(user_data["user_id"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return {"msg": "Invalid refresh token"}, 401

        new_refresh_token = create_refresh_token(
            identity=current_user, additional_claims={"session_id": str(session_id)}
        )
        new_refresh_claims = decode_token(new_refresh_token)
        now = utc_epoch_milliseconds()
        replacement = RefreshToken(
            jti=UUID(str(new_refresh_claims["jti"])),
            session_id=session_id,
            created_at=now,
            expires_at=int(new_refresh_claims["exp"]) * 1000,
        )
        try:
            outcome = SQLAlchemyAuthSessionRepository().rotate_refresh_token(
                session_id, old_jti, replacement, now
            )
        except Exception:
            logger.exception("Refresh rotation failed")
            return {"msg": "Authentication unavailable"}, 503
        if outcome == REUSED:
            logger.warning("Refresh token reuse detected", extra={"user_id": str(user_id)})
            return {"msg": "Refresh token reuse detected"}, 401
        if outcome != ROTATED:
            assert outcome == INACTIVE
            return {"msg": "Refresh token is invalid"}, 401

        new_access_token = create_access_token(
            identity=current_user, additional_claims={"session_id": str(session_id)}
        )

        logger.info("Tokens refreshed successfully", extra={"user": current_user})
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "msg": "Token refreshed successfully",
        }, 200
