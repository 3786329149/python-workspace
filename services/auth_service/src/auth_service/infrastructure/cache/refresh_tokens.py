import json
import time
from uuid import UUID

from redis.asyncio import Redis

from auth_service.application.refresh_tokens import RefreshTokenSession

class RedisRefreshTokenStore:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    def _session_key(self, jti: str) -> str:
        return f"auth:refresh:{jti}"

    def _user_index_key(self, user_id: UUID) -> str:
        return f"auth:user-refresh:{user_id}"

    async def save(self, jti: str, session: RefreshTokenSession) -> None:
        data = {
            "user_id": str(session.user_id),
            "expires_at": session.expires_at,
            "revoked_at": session.revoked_at,
            "replaced_by": session.replaced_by,
        }
        now = int(time.time())
        ttl = max(0, session.expires_at - now)
        if ttl == 0:
            return

        async with self.redis.pipeline() as pipe:
            pipe.set(self._session_key(jti), json.dumps(data), ex=ttl)
            pipe.sadd(self._user_index_key(session.user_id), jti)
            pipe.expire(self._user_index_key(session.user_id), ttl)
            await pipe.execute()

    async def get(self, jti: str) -> RefreshTokenSession | None:
        data = await self.redis.get(self._session_key(jti))
        if not data:
            return None
        
        parsed = json.loads(data)
        return RefreshTokenSession(
            user_id=UUID(parsed["user_id"]),
            expires_at=parsed["expires_at"],
            revoked_at=parsed.get("revoked_at"),
            replaced_by=parsed.get("replaced_by"),
        )

    async def revoke(self, jti: str) -> None:
        session = await self.get(jti)
        if not session:
            return
        
        session.revoked_at = int(time.time())
        await self.save(jti, session)

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        index_key = self._user_index_key(user_id)
        jtis = await self.redis.smembers(index_key)
        
        now = int(time.time())
        async with self.redis.pipeline() as pipe:
            for jti_bytes in jtis:
                jti = jti_bytes.decode('utf-8') if isinstance(jti_bytes, bytes) else jti_bytes
                data = await self.redis.get(self._session_key(jti))
                if data:
                    parsed = json.loads(data)
                    parsed["revoked_at"] = now
                    ttl = max(0, parsed["expires_at"] - now)
                    if ttl > 0:
                        pipe.set(self._session_key(jti), json.dumps(parsed), ex=ttl)
            
            # optional: clear the index? We can keep it to expire naturally.
            # pipe.delete(index_key)
            await pipe.execute()
