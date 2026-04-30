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
