from pathlib import Path

from gateway.config import GatewayConfig, SERVICE_ENV_FILE


def test_gateway_config_defaults() -> None:
    config = GatewayConfig(_env_file=None)

    assert config.PROJECT_NAME == "api-gateway"
    assert config.SERVICE_HOST == "127.0.0.1"
    assert config.SERVICE_PORT == 5600
    assert config.SERVICE_RELOAD is False
    assert config.USER_SERVICE_URL == "http://127.0.0.1:5601"
    assert config.AUTH_SERVICE_URL == "http://127.0.0.1:5602"
    assert config.JWT_SECRET_KEY == "dev-secret-change-me-with-at-least-32-bytes"
    assert config.JWT_ALGORITHM == "HS256"
    assert config.INTERNAL_API_TOKEN == ""
    assert config.RATE_LIMIT_ENABLED is True
    assert config.RATE_LIMIT_REQUESTS == 120
    assert config.RATE_LIMIT_WINDOW_SECONDS == 60
    assert config.CIRCUIT_BREAKER_ENABLED is True
    assert config.CIRCUIT_BREAKER_FAILURE_THRESHOLD == 5
    assert config.CIRCUIT_BREAKER_RECOVERY_SECONDS == 30


def test_gateway_config_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_PORT", "5702")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "10")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "5")
    monkeypatch.setenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "2")
    monkeypatch.setenv("CIRCUIT_BREAKER_RECOVERY_SECONDS", "7")

    config = GatewayConfig(_env_file=None)

    assert config.SERVICE_PORT == 5702
    assert config.RATE_LIMIT_REQUESTS == 10
    assert config.RATE_LIMIT_WINDOW_SECONDS == 5
    assert config.CIRCUIT_BREAKER_FAILURE_THRESHOLD == 2
    assert config.CIRCUIT_BREAKER_RECOVERY_SECONDS == 7


def test_gateway_env_file_path() -> None:
    expected = Path(__file__).resolve().parents[1] / "gateway" / ".env"

    assert SERVICE_ENV_FILE == expected
