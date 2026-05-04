import hashlib
import json
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis
from common.errors import AppError

@dataclass
class IdempotencyState:
    status: str
    response: dict[str, Any] | None = None
    payload_hash: str | None = None

class AuthIdempotencyConflictError(AppError):
    code = "AUTH_IDEMPOTENCY_CONFLICT"
    status_code = 409
    default_message = "idempotency key conflict with different payload"

class AuthRegistrationCompensationFailedError(AppError):
    code = "AUTH_REGISTRATION_COMPENSATION_FAILED"
    status_code = 503
    default_message = "registration failed and compensation failed"

class RegistrationIdempotencyManager:
    def __init__(self, redis: Redis, ttl_seconds: int = 86400) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    def _key(self, idempotency_key: str) -> str:
        return f"auth:idempotency:register:{idempotency_key}"

    def hash_payload(self, email: str, username: str | None) -> str:
        data = f"{email}:{username or ''}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    async def get_state(self, idempotency_key: str) -> IdempotencyState | None:
        data = await self.redis.get(self._key(idempotency_key))
        if not data:
            return None
        parsed = json.loads(data)
        return IdempotencyState(
            status=parsed["status"],
            response=parsed.get("response"),
            payload_hash=parsed.get("payload_hash"),
        )

    async def save_state(self, idempotency_key: str, state: IdempotencyState) -> None:
        data = {
            "status": state.status,
            "response": state.response,
            "payload_hash": state.payload_hash,
        }
        await self.redis.set(
            self._key(idempotency_key),
            json.dumps(data),
            ex=self.ttl_seconds,
        )
