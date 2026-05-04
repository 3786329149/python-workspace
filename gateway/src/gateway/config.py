from functools import lru_cache
from typing import ClassVar

from common.config import BaseServiceConfig, RedisConfigMixin, find_service_env_file
from pydantic_settings import SettingsConfigDict
from pydantic import model_validator

SERVICE_ENV_FILE = find_service_env_file("gateway")


class GatewayConfig(RedisConfigMixin, BaseServiceConfig):
    DEFAULT_SERVICE_PORT: ClassVar[int] = 5600

    PROJECT_NAME: str = "api-gateway"
    USER_SERVICE_URL: str = "http://127.0.0.1:5601"
    AUTH_SERVICE_URL: str = "http://127.0.0.1:5602"
    PROXY_TIMEOUT_SECONDS: float = 10.0
    JWT_SECRET_KEY: str = "dev-secret-change-me-with-at-least-32-bytes"
    JWT_ALGORITHM: str = "HS256"
    INTERNAL_API_TOKEN: str = ""

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    CIRCUIT_BREAKER_ENABLED: bool = True
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_SECONDS: int = 30

    # CORS — comma-separated origins, e.g. "http://localhost:5173,https://example.com"
    # Use "*" to allow all origins (dev only; do NOT use in production with credentials)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    CORS_ALLOW_CREDENTIALS: bool = True

    model_config = SettingsConfigDict(
        env_file=SERVICE_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_prod_config(self) -> 'GatewayConfig':
        if self.ENV != "dev":
            if self.JWT_SECRET_KEY == "dev-secret-change-me-with-at-least-32-bytes":
                raise ValueError("JWT_SECRET_KEY must be changed in production")
            if not self.INTERNAL_API_TOKEN:
                raise ValueError("INTERNAL_API_TOKEN must be configured in production")
            # Usually URL checking might check if they are explicitly passed, but checking if they are the default local host might be okay, or just trust they are set by infra. The requirements specifically say "must be configured". If they are the default, it means they might not be configured, but it's hard to distinguish.
            if self.USER_SERVICE_URL == "http://127.0.0.1:5601":
                raise ValueError("USER_SERVICE_URL must be configured in production")
            if self.AUTH_SERVICE_URL == "http://127.0.0.1:5602":
                raise ValueError("AUTH_SERVICE_URL must be configured in production")
        return self


@lru_cache
def get_settings() -> GatewayConfig:
    return GatewayConfig()


settings = get_settings()
