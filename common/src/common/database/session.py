from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from typing import Protocol


class DatabaseConfig(Protocol):
    DB_POOL_SIZE: int
    DB_MAX_OVERFLOW: int
    async_db_url: str


def create_async_engine_factory(
    config: DatabaseConfig,
    **engine_options: Any,
) -> AsyncEngine:
    options: dict[str, Any] = {
        "pool_pre_ping": True,
        "pool_size": config.DB_POOL_SIZE,
        "max_overflow": config.DB_MAX_OVERFLOW,
    }
    options.update(engine_options)

    return create_async_engine(config.async_db_url, **options)


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
