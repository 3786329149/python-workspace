import asyncio
import bcrypt
from datetime import datetime
from datetime import timedelta
from types import TracebackType
from typing import Self
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from common.security import ACCESS_TOKEN_TYPE, decode_jwt_token
from auth_service.api.deps import get_auth_service
from auth_service.application.commands import LoginCommand, RegisterCommand
from auth_service.application.services import AuthApplicationService
from auth_service.domain.errors import AuthAlreadyExists, AuthInvalidCredentials
from auth_service.domain.models import IdentityType, UserAuth
from auth_service.main import create_app


class InMemoryAuthRepository:
    def __init__(self) -> None:
        self.auths: dict[UUID, UserAuth] = {}

    async def add(self, auth: UserAuth) -> None:
        self.auths[auth.id] = auth

    async def get_by_identifier(
        self,
        identity_type: IdentityType,
        identifier: str,
    ) -> UserAuth | None:
        return next(
            (
                auth
                for auth in self.auths.values()
                if auth.identity_type == identity_type
                and auth.identifier == identifier
                and auth.deleted_at is None
            ),
            None,
        )

    async def get_by_user_id(
        self,
        user_id: UUID,
        identity_type: IdentityType,
    ) -> UserAuth | None:
        return next(
            (
                auth
                for auth in self.auths.values()
                if auth.user_id == user_id
                and auth.identity_type == identity_type
                and auth.deleted_at is None
            ),
            None,
        )

    async def save(self, auth: UserAuth) -> None:
        self.auths[auth.id] = auth


class InMemoryAuthUnitOfWork:
    def __init__(self) -> None:
        self.auths = InMemoryAuthRepository()
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeUserProfiles:
    def __init__(self) -> None:
        self.user_id = uuid4()
        self.deleted_user_ids: list[UUID] = []
        self.request_ids: list[str | None] = []

    async def create_user(
        self,
        *,
        email: str,
        username: str,
        request_id: str | None = None,
    ) -> dict[str, object]:
        self.request_ids.append(request_id)
        return {"id": str(self.user_id), "email": email, "username": username}

    async def delete_user(
        self,
        user_id: UUID,
        *,
        request_id: str | None = None,
    ) -> None:
        self.request_ids.append(request_id)
        self.deleted_user_ids.append(user_id)


class FakeAuthService:
    def __init__(self) -> None:
        self.request_id: str | None = None

    async def register(
        self,
        command: RegisterCommand,
        *,
        request_id: str | None = None,
    ) -> dict[str, str]:
        self.request_id = request_id
        return {
            "user_id": str(uuid4()),
            "email": command.email,
            "username": command.username,
            "message": "User registered successfully",
        }


def test_register_route_is_owned_by_auth_service() -> None:
    app = create_app()
    fake_service = FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: fake_service

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "person@example.com",
                "username": "person",
                "password": "secret123",
            },
            headers={"X-Request-ID": "request-1"},
        )

    assert response.status_code == 201
    assert response.json()["username"] == "person"
    assert fake_service.request_id == "request-1"


def test_register_creates_profile_then_binds_password() -> None:
    async def run() -> None:
        uow = InMemoryAuthUnitOfWork()
        user_profiles = FakeUserProfiles()
        service = AuthApplicationService(uow, user_profiles)

        response = await service.register(
            RegisterCommand(
                email="person@example.com",
                username="person",
                password="secret123",
            ),
            request_id="request-2",
        )

        assert response["user_id"] == str(user_profiles.user_id)
        assert uow.commits == 1
        assert user_profiles.deleted_user_ids == []
        assert user_profiles.request_ids == ["request-2"]

    asyncio.run(run())


def test_register_compensates_profile_when_password_binding_fails() -> None:
    async def run() -> None:
        uow = InMemoryAuthUnitOfWork()
        user_profiles = FakeUserProfiles()
        service = AuthApplicationService(uow, user_profiles)
        existing = UserAuth(
            id=uuid4(),
            user_id=uuid4(),
            identity_type=IdentityType.PASSWORD,
            identifier="person",
            credential="hash",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        await uow.auths.add(existing)

        with pytest.raises(AuthAlreadyExists):
            await service.register(
                RegisterCommand(
                    email="person@example.com",
                    username="person",
                    password="secret123",
                ),
                request_id="request-3",
            )

        assert user_profiles.deleted_user_ids == [user_profiles.user_id]
        assert user_profiles.request_ids == ["request-3", "request-3"]

    asyncio.run(run())


def test_login_returns_access_and_refresh_tokens() -> None:
    async def run() -> None:
        uow = InMemoryAuthUnitOfWork()
        user_id = uuid4()
        hashed_password = bcrypt.hashpw(
            b"secret123",
            bcrypt.gensalt(),
        ).decode("utf-8")
        await uow.auths.add(
            UserAuth(
                id=uuid4(),
                user_id=user_id,
                identity_type=IdentityType.PASSWORD,
                identifier="person",
                credential=hashed_password,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        service = AuthApplicationService(
            uow,
            jwt_secret_key="test-secret-with-at-least-32-bytes",
            access_token_expire_minutes=5,
            refresh_token_expire_days=1,
        )

        response = await service.login(
            LoginCommand(username="person", password="secret123")
        )

        assert response["token_type"] == "bearer"
        assert response["expires_in"] == int(timedelta(minutes=5).total_seconds())
        payload = decode_jwt_token(
            str(response["access_token"]),
            secret_key="test-secret-with-at-least-32-bytes",
            algorithm="HS256",
            expected_type=ACCESS_TOKEN_TYPE,
        )
        assert payload["sub"] == str(user_id)

    asyncio.run(run())


def test_login_rejects_invalid_password() -> None:
    async def run() -> None:
        uow = InMemoryAuthUnitOfWork()
        await uow.auths.add(
            UserAuth(
                id=uuid4(),
                user_id=uuid4(),
                identity_type=IdentityType.PASSWORD,
                identifier="person",
                credential=bcrypt.hashpw(b"secret123", bcrypt.gensalt()).decode(
                    "utf-8"
                ),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        service = AuthApplicationService(uow)

        with pytest.raises(AuthInvalidCredentials):
            await service.login(LoginCommand(username="person", password="wrong123"))

    asyncio.run(run())
