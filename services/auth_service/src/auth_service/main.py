from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from common.database import create_async_engine_factory, create_session_factory
from common.logger import configure_logging, get_logger
from common.redis import create_redis_client
from common.responses import register_common_handlers
from fastapi import FastAPI

from auth_service.config import settings
from auth_service.api.v1.auth import router as auth_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_async_engine_factory(settings)
    redis_client = create_redis_client(settings)
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))

    app.state.db_engine = engine
    app.state.db_session_factory = create_session_factory(engine)
    app.state.redis = redis_client
    app.state.http_client = http_client

    try:
        logger.info("auth service started")
        yield
    finally:
        await http_client.aclose()
        await redis_client.aclose()
        await engine.dispose()
        logger.info("auth service stopped")


def create_app() -> FastAPI:
    configure_logging(settings.LOG_LEVEL)
    app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
    register_common_handlers(app)
    app.include_router(auth_router, prefix="/api/v1")

    @app.get("/")
    def read_root() -> dict[str, str]:
        return {"service": "auth-service"}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
