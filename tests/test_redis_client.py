from app.adapters.statistics.redis_client import create_redis_client


def test_create_redis_client_uses_utf8_responses_without_network(monkeypatch):
    captured: dict[str, object] = {}

    class FakeRedis:
        @classmethod
        def from_url(cls, url: str, **kwargs: object) -> object:
            captured["url"] = url
            captured.update(kwargs)
            return object()

    monkeypatch.setattr(
        "app.adapters.statistics.redis_client.Redis", FakeRedis
    )

    client = create_redis_client("redis://redis:6379/0")

    assert client is not None
    assert captured == {
        "url": "redis://redis:6379/0",
        "decode_responses": True,
    }


def test_create_redis_client_requires_url():
    try:
        create_redis_client("")
    except ValueError as error:
        assert str(error) == "REDIS_URL must be configured"
    else:
        raise AssertionError("Expected REDIS_URL validation error")
