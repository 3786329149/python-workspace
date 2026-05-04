"""PermissionChecker: fetch and cache user permissions for the gateway.

Checks Redis for cached permissions (key: permission:user:{user_id}).
On cache miss, calls user-service GET /api/v1/users/me/permissions via the
internal HTTP client and stores the result with a 5-minute TTL.
"""
from __future__ import annotations

import json
import logging
from uuid import UUID

import httpx
from fastapi import HTTPException, Request, status

from gateway.config import settings

logger = logging.getLogger(__name__)

PERMISSION_TTL = 300  # seconds
_PERM_KEY_PREFIX = "permission:user:"


def _perm_key(user_id: str) -> str:
    return f"{_PERM_KEY_PREFIX}{user_id}"


async def _fetch_from_user_service(
    http_client: httpx.AsyncClient,
    user_id: str,
    request_id: str | None,
) -> list[str]:
    """Call user-service /api/v1/users/me/permissions with internal token."""
    headers: dict[str, str] = {
        "X-User-ID": user_id,
        "X-Internal-Token": settings.INTERNAL_API_TOKEN,
    }
    if request_id:
        headers["X-Request-ID"] = request_id

    url = f"{settings.USER_SERVICE_URL}/api/v1/users/me/permissions"
    try:
        resp = await http_client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data.get("permissions", [])
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "permission fetch failed for user=%s status=%s",
            user_id,
            exc.response.status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="unable to verify permissions",
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("permission fetch error for user=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="unable to verify permissions",
        ) from exc


async def get_user_permissions(request: Request, user_id: str) -> list[str]:
    """Return the permission list for *user_id*, using Redis as L1 cache.

    Args:
        request: FastAPI request (provides app.state.redis and http_client).
        user_id: the user UUID string injected by auth middleware.
    """
    redis = getattr(request.app.state, "redis", None)
    request_id = getattr(request.state, "request_id", None)

    # 1. Try Redis cache
    if redis is not None:
        try:
            raw = await redis.get(_perm_key(user_id))
            if raw is not None:
                return json.loads(raw)
        except Exception as exc:
            logger.debug("redis permission cache read failed: %s", exc)

    # 2. Fetch from user-service
    perms = await _fetch_from_user_service(
        request.app.state.http_client, user_id, request_id
    )

    # 3. Store in Redis
    if redis is not None:
        try:
            await redis.setex(_perm_key(user_id), PERMISSION_TTL, json.dumps(perms))
        except Exception as exc:
            logger.debug("redis permission cache write failed: %s", exc)

    return perms


async def require_permission(request: Request, permission: str) -> None:
    """Raise HTTP 403 if the authenticated user lacks *permission*.

    Intended to be used as a FastAPI dependency or called directly in route
    handlers / proxy logic.
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )

    perms = await get_user_permissions(request, user_id)
    if permission not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"permission '{permission}' required",
        )
