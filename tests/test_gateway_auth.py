import httpx
from datetime import timedelta
from fastapi.testclient import TestClient

from common.security import ACCESS_TOKEN_TYPE, create_jwt_token
from gateway.config import settings
from gateway.core import proxy as gateway_proxy
from gateway.core.circuit_breaker import CircuitBreaker
from gateway.core.rate_limit import InMemoryRateLimiter
from gateway.main import create_app


class FakeHttpClient:
    def __init__(self) -> None:
        self.method = ""
        self.url = ""
        self.content = b""
        self.headers: dict[str, str] = {}
        self.params: list[tuple[str, str]] = []
        self.status_code = 201

    async def request(
        self,
        method: str,
        url: str,
        *,
        content: bytes,
        headers: dict[str, str],
        params: list[tuple[str, str]],
    ) -> httpx.Response:
        self.method = method
        self.url = url
        self.content = content
        self.headers = headers
        self.params = params
        return httpx.Response(
            self.status_code,
            json={
                "user_id": "2cdbf369-b4eb-4e86-8f2f-4ddac07dd336",
                "email": "person@example.com",
                "username": "person",
                "message": "User registered successfully",
            },
            headers={"content-type": "application/json"},
        )

    async def aclose(self) -> None:
        return None


class FailingHttpClient(FakeHttpClient):
    async def request(
        self,
        method: str,
        url: str,
        *,
        content: bytes,
        headers: dict[str, str],
        params: list[tuple[str, str]],
    ) -> httpx.Response:
        raise httpx.ConnectError("connection failed")


def test_gateway_auth_route_is_generic_proxy() -> None:
    app = create_app()
    fake_client = FakeHttpClient()

    with TestClient(app) as client:
        app.state.http_client = fake_client
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "person@example.com",
                "username": "person",
                "password": "secret123",
            },
            headers={"X-Request-ID": "gateway-request"},
        )

    assert response.status_code == 201
    assert response.json()["message"] == "User registered successfully"
    assert fake_client.method == "POST"
    assert fake_client.url.endswith("/api/v1/auth/register")
    assert fake_client.headers["X-Request-ID"] == "gateway-request"
    assert b"secret123" in fake_client.content


def test_gateway_proxy_forwards_query_params(monkeypatch) -> None:
    monkeypatch.setattr(gateway_proxy.settings, "INTERNAL_API_TOKEN", "internal")
    app = create_app()
    fake_client = FakeHttpClient()

    with TestClient(app) as client:
        app.state.http_client = fake_client
        response = client.get(
            "/api/v1/users?include=profile&include=roles",
            headers={
                "X-Request-ID": "query-request",
                "Authorization": f"Bearer {_access_token('user-1')}",
            },
        )

    assert response.status_code == 201
    assert fake_client.method == "GET"
    assert fake_client.url.endswith("/api/v1/users")
    assert fake_client.params == [("include", "profile"), ("include", "roles")]
    assert fake_client.headers["X-User-ID"] == "user-1"
    assert fake_client.headers["X-Internal-Token"] == "internal"


def test_gateway_overwrites_client_internal_token(monkeypatch) -> None:
    monkeypatch.setattr(gateway_proxy.settings, "INTERNAL_API_TOKEN", "internal")
    app = create_app()
    fake_client = FakeHttpClient()

    with TestClient(app) as client:
        app.state.http_client = fake_client
        response = client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {_access_token('user-1')}",
                "X-Internal-Token": "spoofed",
                "X-User-ID": "spoofed",
            },
        )

    assert response.status_code == 201
    assert fake_client.headers["X-Internal-Token"] == "internal"
    assert fake_client.headers["X-User-ID"] == "user-1"


def test_gateway_blocks_protected_route_without_token() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/users",
            headers={"X-Request-ID": "query-request"},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_gateway_rate_limit_blocks_excess_requests() -> None:
    app = create_app()

    with TestClient(app) as client:
        app.state.http_client = FakeHttpClient()
        app.state.rate_limiter = InMemoryRateLimiter(
            requests=1,
            window_seconds=60,
        )

        first = client.post("/api/v1/auth/register", json={})
        second = client.post("/api/v1/auth/register", json={})

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.headers["Retry-After"]


def test_gateway_circuit_breaker_opens_after_upstream_failure() -> None:
    app = create_app()

    with TestClient(app) as client:
        app.state.http_client = FailingHttpClient()
        app.state.circuit_breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_seconds=60,
        )

        first = client.post("/api/v1/auth/register", json={})
        second = client.post("/api/v1/auth/register", json={})

    assert first.status_code == 502
    assert second.status_code == 503
    assert second.headers["Retry-After"]


def _access_token(user_id: str) -> str:
    return create_jwt_token(
        subject=user_id,
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expires_delta=timedelta(minutes=5),
        token_type=ACCESS_TOKEN_TYPE,
    )
