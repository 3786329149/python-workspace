import httpx
from fastapi.testclient import TestClient

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


def test_gateway_proxy_forwards_query_params() -> None:
    app = create_app()
    fake_client = FakeHttpClient()

    with TestClient(app) as client:
        app.state.http_client = fake_client
        response = client.get(
            "/api/v1/auth/sessions?include=profile&include=roles",
            headers={"X-Request-ID": "query-request"},
        )

    assert response.status_code == 201
    assert fake_client.method == "GET"
    assert fake_client.url.endswith("/api/v1/auth/sessions")
    assert fake_client.params == [("include", "profile"), ("include", "roles")]


def test_gateway_rate_limit_blocks_excess_requests() -> None:
    app = create_app()

    with TestClient(app) as client:
        app.state.http_client = FakeHttpClient()
        app.state.rate_limiter = InMemoryRateLimiter(
            requests=1,
            window_seconds=60,
        )

        first = client.get("/api/v1/auth/health")
        second = client.get("/api/v1/auth/health")

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

        first = client.get("/api/v1/auth/health")
        second = client.get("/api/v1/auth/health")

    assert first.status_code == 502
    assert second.status_code == 503
    assert second.headers["Retry-After"]
