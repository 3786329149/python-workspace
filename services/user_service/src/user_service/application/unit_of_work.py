from types import TracebackType
from typing import Protocol, Self

from user_service.domain.repositories import DepartmentRepository, MenuRepository, RoleRepository, UserRepository


class UserUnitOfWork(Protocol):
    users: UserRepository
    roles: RoleRepository
    menus: MenuRepository
    departments: DepartmentRepository

    """ 进入上下文时调用,应返回一个对象(通常是self) """
    async def __aenter__(self) -> Self: ...

    """ 退出上下文时调用(无论成功或失败),用于处理异常或清理资源 """
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    """ 提交事务 (如果需要) """
    async def commit(self) -> None: ...

    """ 回滚事务 (如果需要) """
    async def rollback(self) -> None: ...
