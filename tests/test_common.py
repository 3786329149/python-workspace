from pathlib import Path

from common.config import BaseServiceConfig, find_service_env_file
from common.errors import AppError


def test_common_modules_import() -> None:
    import common.config
    import common.database
    import common.errors
    import common.logger
    import common.redis
    import common.responses

    assert common.config.BaseServiceConfig
    assert common.config.DatabaseConfigMixin
    assert common.config.RedisConfigMixin
    assert common.database.create_async_engine_factory
    assert common.database.Base
    assert common.errors.AppError
    assert common.logger.get_logger
    assert common.redis.create_redis_client
    assert common.responses.error_response


def test_config_reads_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SERVICE_PORT", "5800")

    config = BaseServiceConfig(_env_file=None)

    assert config.LOG_LEVEL == "DEBUG"
    assert config.ENV == "dev"
    assert config.SERVICE_HOST == "127.0.0.1"
    assert config.SERVICE_PORT == 5800
    assert config.SERVICE_RELOAD is False


def test_find_service_env_file_points_to_service_env() -> None:
    expected = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "user_service"
        / ".env"
    )

    assert find_service_env_file("user_service") == expected


def test_app_error_defaults_can_be_overridden() -> None:
    error = AppError("nope", code="NOPE", status_code=418)

    assert str(error) == "nope"
    assert error.code == "NOPE"
    assert error.status_code == 418
