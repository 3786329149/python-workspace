from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from user_service.api.deps import get_user_service
from user_service.domain.errors import UserAlreadyExists
from user_service.domain.models import User, UserStatus
from user_service.main import create_app


class FakeUserService:
    async def create_user(self, command):
        now = datetime.now(UTC)
        return User(
            id=uuid4(),
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
