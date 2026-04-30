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
    DEFAULT_SERVICE_PORT: ClassVar[int] = 5602

    PROJECT_NAME: str = "auth-service"
    USER_SERVICE_URL: str = "http://127.0.0.1:5601"
    INTERNAL_API_TOKEN: str = ""
    JWT_SECRET_KEY: str = "dev-secret-change-me-with-at-least-32-bytes"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=SERVICE_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> AuthServiceConfig:
    return AuthServiceConfig()


settings = get_settings()
