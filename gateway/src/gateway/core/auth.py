from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from common.errors import AppError
from common.responses import REQUEST_ID_HEADER, error_response
from common.security import ACCESS_TOKEN_TYPE, decode_jwt_token
from gateway.config import settings

PUBLIC_PATHS = {
    "/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def register_auth_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def auth_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if _is_public_request(request):
            return await call_next(request)

        try:
            token = _bearer_token(request)
            payload = decode_jwt_token(
                token,
                secret_key=settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM,
                expected_type=ACCESS_TOKEN_TYPE,
            )
        except AppError as exc:
            return _auth_error_response(request, exc)

        request.state.user_id = str(payload["sub"])
        return await call_next(request)


def _is_public_request(request: Request) -> bool:
    if request.method == "OPTIONS":
        return True
    return request.url.path in PUBLIC_PATHS


def _bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AppError(
            "missing bearer token",
            code="AUTH_REQUIRED",
            status_code=401,
        )
    return token


def _auth_error_response(request: Request, exc: AppError) -> JSONResponse:
    request_id = (
        getattr(request.state, "request_id", None)
        or request.headers.get(REQUEST_ID_HEADER)
        or str(uuid4())
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            code=exc.code,
            message=exc.message,
            request_id=request_id,
        ),
        headers={REQUEST_ID_HEADER: request_id},
    )
