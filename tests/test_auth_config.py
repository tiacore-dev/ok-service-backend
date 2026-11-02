from datetime import timedelta

from config import Config


def test_auth_access_token_default_expiration_is_30_minutes():
    assert Config.JWT_ACCESS_TOKEN_EXPIRES == timedelta(minutes=30)
