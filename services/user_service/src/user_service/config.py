from functools import lru_cache

from common.config import (
    BaseServiceConfig,
    DatabaseConfigMixin,
    RedisConfigMixin,
    find_service_env_file,
)
from pydantic_settings import SettingsConfigDict

SERVICE_ENV_FILE = find_service_env_file("user_service")


class UserServiceConfig(
    DatabaseConfigMixin,
    RedisConfigMixin,
    BaseServiceConfig,
):
    PROJECT_NAME: str = "user-service"

    model_config = SettingsConfigDict(
        env_file=SERVICE_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> UserServiceConfig:
    return UserServiceConfig()


settings = get_settings()
