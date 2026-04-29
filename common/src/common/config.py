from pathlib import Path
from typing import ClassVar
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_workspace_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    candidates = (current, *current.parents)

    for candidate in candidates:
        pyproject = candidate / "pyproject.toml"
        if not pyproject.exists():
            continue

        try:
            if "[tool.uv.workspace]" in pyproject.read_text(encoding="utf-8"):
                return candidate
        except OSError:
            continue

    return current


WORKSPACE_ROOT = find_workspace_root()
ENV_FILE = WORKSPACE_ROOT / ".env"


def find_service_root(service: str | Path) -> Path:
    service_path = Path(service)
    if service_path.is_absolute():
        return service_path

    candidates = (
        WORKSPACE_ROOT / service_path,
        WORKSPACE_ROOT / "services" / service_path,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[-1]


def find_service_env_file(service: str | Path, filename: str = ".env") -> Path:
    return find_service_root(service) / filename


class BaseServiceConfig(BaseSettings):
    DEFAULT_SERVICE_HOST: ClassVar[str] = "127.0.0.1"
    DEFAULT_SERVICE_PORT: ClassVar[int] = 8000
    DEFAULT_SERVICE_RELOAD: ClassVar[bool] = False

    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    SERVICE_HOST: str = ""
    SERVICE_PORT: int = 0
    SERVICE_RELOAD: bool | None = None

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def fill_service_defaults(self):
        if not self.SERVICE_HOST:
            self.SERVICE_HOST = self.DEFAULT_SERVICE_HOST
        if not self.SERVICE_PORT:
            self.SERVICE_PORT = self.DEFAULT_SERVICE_PORT
        if self.SERVICE_RELOAD is None:
            self.SERVICE_RELOAD = self.DEFAULT_SERVICE_RELOAD
        return self


class DatabaseConfigMixin:
    DEFAULT_DB_NAME: ClassVar[str] = "user_db"

    DATABASE_URL: str | None = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASS: str = ""
    DB_NAME: str = ""
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    @model_validator(mode="after")
    def fill_database_defaults(self):
        if not self.DB_NAME:
            self.DB_NAME = self.DEFAULT_DB_NAME
        return self

    @property
    def async_db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL

        user = quote_plus(self.DB_USER)
        password = f":{quote_plus(self.DB_PASS)}" if self.DB_PASS else ""
        return (
            f"postgresql+asyncpg://{user}{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


class RedisConfigMixin:
    DEFAULT_REDIS_URL: ClassVar[str] = "redis://localhost:6379/0"

    REDIS_URL: str = ""

    @model_validator(mode="after")
    def fill_redis_defaults(self):
        if not self.REDIS_URL:
            self.REDIS_URL = self.DEFAULT_REDIS_URL
        return self
