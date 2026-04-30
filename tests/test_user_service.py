from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from user_service.api import deps as user_deps
from user_service.api.deps import get_user_service
from user_service.domain.errors import UserAlreadyExists
from user_service.domain.models import User, UserStatus
from user_service.main import create_app


class FakeUserService:
    def __init__(self) -> None:
        self.user_id = uuid4()

    async def create_user(self, command):
        now = datetime.now(UTC)
        return User(
            id=self.user_id,
            tenant_id=command.tenant_id,
            email=command.email,
            username=command.username,
            nickname=command.nickname or command.display_name,
            phone=command.phone,
            avatar_url=command.avatar_url,
            status=UserStatus.ACTIVE,
            is_admin=command.is_admin,
            dept_id=command.dept_id,
            created_at=now,
            updated_at=now,
        )

    async def get_user(self, user_id: UUID):
        now = datetime.now(UTC)
        return User(
            id=user_id,
            tenant_id=None,
            email="person@example.com",
            username="person",
            nickname="Person",
            phone=None,
            avatar_url=None,
            status=UserStatus.ACTIVE,
            is_admin=False,
            dept_id=None,
            created_at=now,
            updated_at=now,
        )


class ConflictUserService:
    async def create_user(self, command):
        raise UserAlreadyExists()


def test_root_route() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_create_user_route() -> None:
    app = create_app()
    app.dependency_overrides[get_user_service] = lambda: FakeUserService()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/users",
            json={"email": "person@example.com", "display_name": "Person"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "person@example.com"
    assert body["display_name"] == "Person"
    assert body["status"] == "active"


def test_app_error_response_shape() -> None:
    app = create_app()
    app.dependency_overrides[get_user_service] = lambda: ConflictUserService()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/users",
            json={"email": "person@example.com"},
            headers={"X-Request-ID": "test-request"},
        )

    assert response.status_code == 409
    assert response.headers["X-Request-ID"] == "test-request"
    assert response.json() == {
        "code": "USER_ALREADY_EXISTS",
        "message": "user already exists",
        "request_id": "test-request",
    }


def test_get_current_user_route(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[get_user_service] = lambda: FakeUserService()
    monkeypatch.setattr(user_deps.settings, "INTERNAL_API_TOKEN", "internal")
    user_id = uuid4()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/users/me",
            headers={
                "X-Internal-Token": "internal",
                "X-User-ID": str(user_id),
            },
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(user_id)


def test_get_current_user_rejects_missing_internal_token(monkeypatch) -> None:
    app = create_app()
    monkeypatch.setattr(user_deps.settings, "INTERNAL_API_TOKEN", "internal")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/users/me",
            headers={"X-User-ID": str(uuid4())},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "USER_INTERNAL_AUTH_FAILED"
