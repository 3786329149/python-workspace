from typing import Any
from typing import Protocol

from redis.asyncio import Redis, from_url


class RedisConfig(Protocol):
    REDIS_URL: str


def create_redis_client(
    config: RedisConfig,
    **redis_options: Any,
) -> Redis:
    return from_url(
        config.REDIS_URL,
        decode_responses=True,
        **redis_options,
    )
