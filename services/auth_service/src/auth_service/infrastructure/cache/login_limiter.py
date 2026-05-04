import time
from redis.asyncio import Redis

from auth_service.domain.errors import AuthInvalidCredentials
from common.errors import AppError

class RedisLoginAttemptLimiter:
    def __init__(
        self,
        redis: Redis,
        window_seconds: int = 900,
        max_by_username: int = 5,
        max_by_ip: int = 30,
        lock_seconds: int = 900,
    ) -> None:
        self.redis = redis
        self.window_seconds = window_seconds
        self.max_by_username = max_by_username
        self.max_by_ip = max_by_ip
        self.lock_seconds = lock_seconds

    def _username_key(self, username: str) -> str:
        return f"auth:login_fails:user:{username}"

    def _ip_key(self, ip_address: str) -> str:
        return f"auth:login_fails:ip:{ip_address}"

    async def check_limits(self, username: str, ip_address: str) -> None:
        user_key = self._username_key(username)
        ip_key = self._ip_key(ip_address)
        
        async with self.redis.pipeline() as pipe:
            pipe.get(user_key)
            pipe.get(ip_key)
            results = await pipe.execute()
            
        user_fails = int(results[0]) if results[0] else 0
        ip_fails = int(results[1]) if results[1] else 0
        
        if user_fails >= self.max_by_username or ip_fails >= self.max_by_ip:
            raise AppError("too many login attempts", code="AUTH_TOO_MANY_REQUESTS", status_code=429)

    async def record_failure(self, username: str, ip_address: str) -> None:
        user_key = self._username_key(username)
        ip_key = self._ip_key(ip_address)
        
        async with self.redis.pipeline() as pipe:
            for key in (user_key, ip_key):
                pipe.incr(key)
            results = await pipe.execute()
            
        # We need to set expiration if it's the first failure.
        # It's easier to just always expire from now or use expire if ttl is -1.
        # We'll use a simpler approach: check TTL and set it if missing, or use set(EX) logic.
        async with self.redis.pipeline() as pipe:
            for i, key in enumerate((user_key, ip_key)):
                if results[i] == 1:
                    pipe.expire(key, self.window_seconds)
                else:
                    # If it reaches max, extend lock time to lock_seconds
                    limit = self.max_by_username if i == 0 else self.max_by_ip
                    if results[i] >= limit:
                        pipe.expire(key, self.lock_seconds)
            await pipe.execute()

    async def clear_failures(self, username: str) -> None:
        # We only clear username failures, not IP failures (IP might be shared and we don't want an attacker
        # to clear IP limits by logging into a valid account).
        await self.redis.delete(self._username_key(username))
