import asyncio
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from user_service.application.commands import CreateUserCommand
from user_service.application.services import UserApplicationService
from user_service.domain.errors import UserAlreadyExists
from user_service.domain.models import User, normalize_email


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}

    async def add(self, user: User) -> None:
        self.users[user.id] = user

    async def save(self, user: User) -> None:
        self.users[user.id] = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        normalized = normalize_email(email)
        return next(
            (user for user in self.users.values() if user.email == normalized),
            None,
        )

    async def get_by_username(self, username: str) -> User | None:
        return next(
            (user for user in self.users.values() if user.username == username),
            None,
        )

    async def get_by_phone(self, phone: str) -> User | None:
        return next(
            (user for user in self.users.values() if user.phone == phone),
            None,
        )


class InMemoryUnitOfWork:
    def __init__(self) -> None:
        self.users = InMemoryUserRepository()
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
        if exc_type:
            await self.rollback()

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class InMemoryCache:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}

    async def get_user(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    async def set_user(self, user: User) -> None:
        self.users[user.id] = user

    async def delete_user(self, user_id: UUID) -> None:
        self.users.pop(user_id, None)


def test_create_user_normalizes_and_caches() -> None:
    async def run() -> None:
        uow = InMemoryUnitOfWork()
        cache = InMemoryCache()
        service = UserApplicationService(uow, cache)

        user = await service.create_user(
            CreateUserCommand(email="  PERSON@Example.COM  ", username="person")
        )

        assert user.email == "person@example.com"
        assert uow.commits == 1
        assert await cache.get_user(user.id) == user

    asyncio.run(run())


def test_duplicate_email_is_rejected() -> None:
    async def run() -> None:
        service = UserApplicationService(InMemoryUnitOfWork(), InMemoryCache())
        await service.create_user(CreateUserCommand(email="person@example.com"))

        with pytest.raises(UserAlreadyExists):
            await service.create_user(CreateUserCommand(email="PERSON@example.com"))

    asyncio.run(run())
