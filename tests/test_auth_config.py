from auth_service.config import AuthServiceConfig


def test_auth_service_config_defaults() -> None:
    config = AuthServiceConfig(_env_file=None)

    assert config.PROJECT_NAME == "auth-service"
    assert config.DB_NAME == "auth_db"
    assert config.REDIS_URL == "redis://localhost:6379/1"
    assert config.SERVICE_PORT == 5601
    assert config.async_db_url == "postgresql+asyncpg://postgres@localhost:5432/auth_db"
