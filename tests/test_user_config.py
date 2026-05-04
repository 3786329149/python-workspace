from pathlib import Path

from user_service.config import SERVICE_ENV_FILE, UserServiceConfig


def test_user_service_config_defaults() -> None:
    config = UserServiceConfig(_env_file=None)

    assert config.PROJECT_NAME == "user-service"
    assert config.DB_NAME == "user_db"
    assert config.REDIS_URL == "redis://localhost:6379/0"
    assert config.SERVICE_PORT == 5601
    assert config.INTERNAL_API_TOKEN == ""
    assert config.async_db_url == "postgresql+asyncpg://postgres@localhost:5432/user_db"


def test_user_service_config_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("PROJECT_NAME", "users")
    monkeypatch.setenv("DB_NAME", "users_db")
    monkeypatch.setenv("DB_PASS", "secret")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/9")
    monkeypatch.setenv("SERVICE_PORT", "5701")

    config = UserServiceConfig(_env_file=None)

    assert config.PROJECT_NAME == "users"
    assert config.REDIS_URL == "redis://localhost:6379/9"
    assert config.SERVICE_PORT == 5701
    assert config.async_db_url == "postgresql+asyncpg://postgres:secret@localhost:5432/users_db"


def test_user_service_env_file_path() -> None:
    expected = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "user_service"
        / ".env"
    )

    assert SERVICE_ENV_FILE == expected


import pytest
from pydantic import ValidationError

def test_user_config_prod_validation() -> None:
    # default should fail if env=prod
    with pytest.raises(ValidationError) as exc:
        UserServiceConfig(_env_file=None, ENV="prod")
    
    assert "INTERNAL_API_TOKEN must be configured" in str(exc.value)

    # With proper settings, it should pass
    config = UserServiceConfig(
        _env_file=None, 
        ENV="prod", 
        INTERNAL_API_TOKEN="super-secret",
    )
    assert config.INTERNAL_API_TOKEN == "super-secret"
