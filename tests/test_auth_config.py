import importlib
from datetime import timedelta

import config


def test_auth_access_token_default_expiration_is_30_minutes(monkeypatch):
    try:
        with monkeypatch.context() as context:
            context.delenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", raising=False)
            default_config = importlib.reload(config)
            assert default_config.Config.JWT_ACCESS_TOKEN_EXPIRES == timedelta(
                minutes=30
            )
    finally:
        importlib.reload(config)
