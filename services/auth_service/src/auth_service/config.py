from functools import lru_cache
from typing import ClassVar

from common.config import (
    BaseServiceConfig,
    DatabaseConfigMixin,
    RedisConfigMixin,
    find_service_env_file,
)
from pydantic_settings import SettingsConfigDict

SERVICE_ENV_FILE = find_service_env_file("auth_service")


class AuthServiceConfig(
    DatabaseConfigMixin,
    RedisConfigMixin,
    BaseServiceConfig,
):
    DEFAULT_DB_NAME: ClassVar[str] = "auth_db"
    DEFAULT_REDIS_URL: ClassVar[str] = "redis://localhost:6379/1"
    DEFAULT_SERVICE_PORT: ClassVar[int] = 5601

    PROJECT_NAME: str = "auth-service"

    model_config = SettingsConfigDict(
        env_file=SERVICE_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> AuthServiceConfig:
    return AuthServiceConfig()


settings = get_settings()
