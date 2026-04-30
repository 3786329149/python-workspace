from functools import lru_cache
from typing import ClassVar

from common.config import BaseServiceConfig, find_service_env_file
from pydantic_settings import SettingsConfigDict

SERVICE_ENV_FILE = find_service_env_file("gateway")


class GatewayConfig(BaseServiceConfig):
    DEFAULT_SERVICE_PORT: ClassVar[int] = 5600

    PROJECT_NAME: str = "api-gateway"
    USER_SERVICE_URL: str = "http://127.0.0.1:5601"
    AUTH_SERVICE_URL: str = "http://127.0.0.1:5602"
    PROXY_TIMEOUT_SECONDS: float = 10.0
    JWT_SECRET_KEY: str = "dev-secret-change-me-with-at-least-32-bytes"
    JWT_ALGORITHM: str = "HS256"

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    CIRCUIT_BREAKER_ENABLED: bool = True
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_SECONDS: int = 30

    model_config = SettingsConfigDict(
        env_file=SERVICE_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> GatewayConfig:
    return GatewayConfig()


settings = get_settings()
