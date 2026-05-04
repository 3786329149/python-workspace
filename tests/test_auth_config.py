from auth_service.config import AuthServiceConfig


def test_auth_service_config_defaults() -> None:
    config = AuthServiceConfig(_env_file=None)

    assert config.PROJECT_NAME == "auth-service"
    assert config.DB_NAME == "auth_db"
    assert config.REDIS_URL == "redis://localhost:6379/1"
    assert config.SERVICE_PORT == 5602
    assert config.USER_SERVICE_URL == "http://127.0.0.1:5601"
    assert config.JWT_SECRET_KEY == "dev-secret-change-me-with-at-least-32-bytes"
    assert config.JWT_ALGORITHM == "HS256"
    assert config.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert config.REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert config.async_db_url == "postgresql+asyncpg://postgres@localhost:5432/auth_db"


import pytest
from pydantic import ValidationError

def test_auth_config_prod_validation() -> None:
    # default should fail if env=prod
    with pytest.raises(ValidationError) as exc:
        AuthServiceConfig(_env_file=None, ENV="prod")
    
    assert "JWT_SECRET_KEY must be changed" in str(exc.value)

    # Missing internal api token
    with pytest.raises(ValidationError) as exc:
        AuthServiceConfig(_env_file=None, ENV="prod", JWT_SECRET_KEY="new-secret-key-12345678901234567890")
    
    assert "INTERNAL_API_TOKEN must be configured" in str(exc.value)

    # With proper settings, it should pass
    config = AuthServiceConfig(
        _env_file=None, 
        ENV="prod", 
        JWT_SECRET_KEY="new-secret-key-12345678901234567890",
        INTERNAL_API_TOKEN="super-secret",
        USER_SERVICE_URL="http://user-service:5601",
    )
    assert config.INTERNAL_API_TOKEN == "super-secret"
