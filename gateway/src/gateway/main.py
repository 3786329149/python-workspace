from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from common.logger import configure_logging
from common.redis import create_redis_client
from common.responses import register_common_handlers
from gateway.config import settings
from gateway.api.v1.proxy import router as proxy_router
from gateway.core.auth import register_auth_middleware
from gateway.core.circuit_breaker import CircuitBreaker
from gateway.core.rate_limit import InMemoryRateLimiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.PROXY_TIMEOUT_SECONDS)
    )
    redis_client = create_redis_client(settings)
    app.state.http_client = http_client
    app.state.redis = redis_client
    app.state.rate_limiter = InMemoryRateLimiter(
        requests=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        enabled=settings.RATE_LIMIT_ENABLED,
    )
    app.state.circuit_breaker = CircuitBreaker(
        failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_seconds=settings.CIRCUIT_BREAKER_RECOVERY_SECONDS,
        enabled=settings.CIRCUIT_BREAKER_ENABLED,
    )
    try:
        yield
    finally:
        await http_client.aclose()
        await redis_client.aclose()


def create_app() -> FastAPI:
    configure_logging(settings.LOG_LEVEL)
    app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
    register_common_handlers(app)

    # CORS — must be registered BEFORE the auth middleware so that
    # OPTIONS preflight requests are handled and never reach auth checks.
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    register_auth_middleware(app)
    app.include_router(proxy_router, prefix="/api/v1")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "gateway"}

    return app

app = create_app()
