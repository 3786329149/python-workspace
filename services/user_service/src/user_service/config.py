from functools import lru_cache
from typing import ClassVar

from common.config import (
    BaseServiceConfig,
    DatabaseConfigMixin,
    RedisConfigMixin,
    find_service_env_file,
)
from pydantic_settings import SettingsConfigDict
from pydantic import model_validator

SERVICE_ENV_FILE = find_service_env_file("user_service")


class UserServiceConfig(
    DatabaseConfigMixin,
    RedisConfigMixin,
    BaseServiceConfig,
):
    DEFAULT_SERVICE_PORT: ClassVar[int] = 5601

    PROJECT_NAME: str = "user-service"
    INTERNAL_API_TOKEN: str = ""
    AUTH_SERVICE_URL: str = "http://127.0.0.1:5602"

    model_config = SettingsConfigDict(
        env_file=SERVICE_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_prod_config(self) -> 'UserServiceConfig':
        if self.ENV != "dev":
            if not self.INTERNAL_API_TOKEN or len(self.INTERNAL_API_TOKEN) < 32:
                raise ValueError("INTERNAL_API_TOKEN must be at least 32 characters in production")
        return self


@lru_cache
def get_settings() -> UserServiceConfig:
    return UserServiceConfig()


settings = get_settings()
