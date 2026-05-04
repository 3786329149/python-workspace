from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from common.errors import AppError

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class TokenError(AppError):
    code = "TOKEN_INVALID"
    status_code = 401
    default_message = "invalid token"


class TokenExpired(TokenError):
    code = "TOKEN_EXPIRED"
    default_message = "token expired"


def create_jwt_token(
    *,
    subject: str,
    secret_key: str,
    algorithm: str,
    expires_delta: timedelta,
    token_type: str,
    claims: dict[str, Any] | None = None,
    jti: str | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if jti:
        payload["jti"] = jti
    if claims:
        payload.update(claims)
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_jwt_token(
    token: str,
    *,
    secret_key: str,
    algorithm: str,
    expected_type: str | None = None,
) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpired() from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError() from exc

    if expected_type and payload.get("type") != expected_type:
        raise TokenError("invalid token type")
    if not payload.get("sub"):
        raise TokenError("missing token subject")
    return payload
