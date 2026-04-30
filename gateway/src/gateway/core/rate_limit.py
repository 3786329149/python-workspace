import asyncio
import time
from dataclasses import dataclass


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("rate limit exceeded")


@dataclass(slots=True)
class RateLimitBucket:
    window_started_at: float
    count: int


class InMemoryRateLimiter:
    def __init__(
        self,
        *,
        requests: int,
        window_seconds: int,
        enabled: bool = True,
    ) -> None:
        self.requests = requests
        self.window_seconds = window_seconds
        self.enabled = enabled
        self._buckets: dict[str, RateLimitBucket] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> None:
        if not self.enabled:
            return

        now = time.monotonic()
        async with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None or now - bucket.window_started_at >= self.window_seconds:
                self._buckets[key] = RateLimitBucket(now, 1)
                return

            if bucket.count >= self.requests:
                retry_after = max(
                    1,
                    int(self.window_seconds - (now - bucket.window_started_at)),
                )
                raise RateLimitExceeded(retry_after)

            bucket.count += 1
