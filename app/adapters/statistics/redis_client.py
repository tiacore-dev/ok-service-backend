"""Redis client factory for cached project-work statistics.

The factory deliberately does not call ``ping``: redis-py opens a connection
only when a command is executed.  Statistics read/write behaviour is added in
a later vertical slice.
"""

from typing import Protocol

from redis import Redis


class RedisClient(Protocol):
    def get(self, name: str) -> str | bytes | None: ...

    def set(self, name: str, value: str) -> object: ...

    def delete(self, *names: str) -> object: ...


def create_redis_client(redis_url: str) -> Redis:
    """Create a UTF-8 Redis client without performing network I/O."""
    if not redis_url:
        raise ValueError("REDIS_URL must be configured")
    return Redis.from_url(redis_url, decode_responses=True)
