import json
from datetime import datetime
from uuid import UUID

from redis.asyncio import Redis

from user_service.domain.models import User, UserStatus


class RedisUserCache:
    def __init__(self, redis: Redis, ttl_seconds: int = 900) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    async def get_user(self, user_id: UUID) -> User | None:
        raw = await self.redis.get(self._user_key(user_id))
        if raw is None:
            return None

        data = json.loads(raw)
        return User(
            id=UUID(data["id"]),
            tenant_id=UUID(data["tenant_id"]) if data["tenant_id"] else None,
            email=data["email"],
            username=data["username"],
            nickname=data["nickname"],
            phone=data["phone"],
            avatar_url=data["avatar_url"],
            status=UserStatus(data["status"]),
            is_admin=data["is_admin"],
            dept_id=UUID(data["dept_id"]) if data["dept_id"] else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            deleted_at=(
                datetime.fromisoformat(data["deleted_at"])
                if data["deleted_at"] is not None
                else None
            ),
        )

    async def set_user(self, user: User) -> None:
        await self.redis.setex(
            self._user_key(user.id),
            self.ttl_seconds,
            json.dumps(self._serialize(user)),
        )

    async def delete_user(self, user_id: UUID) -> None:
        await self.redis.delete(self._user_key(user_id))

    def _user_key(self, user_id: UUID) -> str:
        return f"user:{user_id}"

    def _permission_key(self, user_id: UUID) -> str:
        return f"permission:user:{user_id}"

    async def get_permissions(self, user_id: UUID) -> list[str] | None:
        raw = await self.redis.get(self._permission_key(user_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def set_permissions(self, user_id: UUID, perms: list[str], *, ttl: int = 300) -> None:
        await self.redis.setex(
            self._permission_key(user_id),
            ttl,
            json.dumps(perms),
        )

    async def delete_permissions(self, user_id: UUID) -> None:
        await self.redis.delete(self._permission_key(user_id))

    def _serialize(self, user: User) -> dict[str, str | None]:
        return {
            "id": str(user.id),
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "email": user.email,
            "username": user.username,
            "nickname": user.nickname,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
            "status": user.status.value,
            "is_admin": user.is_admin,
            "dept_id": str(user.dept_id) if user.dept_id else None,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
        }
