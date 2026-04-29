from types import TracebackType
from typing import Protocol, Self
from auth_service.domain.repositories import AuthRepository

class AuthUnitOfWork(Protocol):
    auths: AuthRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
