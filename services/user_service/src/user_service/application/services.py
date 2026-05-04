from user_service.application.cache import UserCache
from user_service.application.commands import (
    CreateRegistrationProfileCommand,
    CreateUserCommand,
    UpdateUserProfileCommand,
    UserIdCommand,
)
from user_service.application.unit_of_work import UserUnitOfWork
from user_service.domain.errors import UserAlreadyExists, UserNotFound
from user_service.domain.models import Role, User, UserStatus, normalize_email, normalize_optional

PERMISSION_CACHE_TTL = 300  # 5 minutes


class UserApplicationService:
    def __init__(self, uow: UserUnitOfWork, cache: UserCache | None = None) -> None:
        self.uow = uow
        self.cache = cache

    async def get_user_permissions(self, user_id: UUID) -> list[str]:
        """Get unique permission keys for a user (non-null perms from menus, type=F).
        Checks Redis first; falls back to DB and caches the result."""
        cached = await self._get_permission_cache(user_id)
        if cached is not None:
            return cached

        async with self.uow:
            menus = await self.uow.menus.get_by_user_id(user_id)

        perms = sorted(
            {m.perms for m in menus if m.perms and m.menu_type == "F"}
        )
        await self._set_permission_cache(user_id, perms)
        return perms

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> None:
        """Assign a role to a user and invalidate the user's permission cache."""
        async with self.uow:
            user = await self.uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFound("user not found")
            role = await self.uow.roles.get_by_id(role_id)
            if role is None:
                from common.errors import AppError
                raise AppError("role not found", code="ROLE_NOT_FOUND", status_code=404)
            await self.uow.roles.assign_role_to_user(user_id, role_id)
            await self.uow.commit()

        await self._delete_permission_cache(user_id)

    async def create_user(self, command: CreateUserCommand) -> User:
        email = normalize_email(command.email)
        username = normalize_optional(command.username)
        phone = normalize_optional(command.phone)

        async with self.uow:
            if await self.uow.users.get_by_email(email):
                raise UserAlreadyExists("email already exists")
            if username and await self.uow.users.get_by_username(username):
                raise UserAlreadyExists("username already exists")
            if phone and await self.uow.users.get_by_phone(phone):
                raise UserAlreadyExists("phone already exists")

            user = User.create(
                email=email,
                tenant_id=command.tenant_id,
                username=username,
                display_name=command.display_name,
                nickname=command.nickname,
                phone=phone,
                avatar_url=command.avatar_url,
                is_admin=command.is_admin,
                dept_id=command.dept_id,
            )
            await self.uow.users.add(user)
            await self.uow.commit()

        await self._set_cache(user)
        return user

    async def create_registration_profile(self, command: CreateRegistrationProfileCommand) -> User:
        email = normalize_email(command.email)
        username = normalize_optional(command.username)

        async with self.uow:
            if await self.uow.users.get_by_email(email):
                raise UserAlreadyExists("email already exists")
            if username and await self.uow.users.get_by_username(username):
                raise UserAlreadyExists("username already exists")

            user = User.create(
                email=email,
                username=username,
                status=UserStatus.PENDING,
            )
            await self.uow.users.add(user)
            await self.uow.commit()

        await self._set_cache(user)
        return user

    async def get_user(self, user_id: UUID) -> User:
        cached = await self._get_cache(user_id)
        if cached:
            return cached

        async with self.uow:
            user = await self.uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFound("user not found")

        await self._set_cache(user)
        return user

    async def get_user_by_email(self, email: str) -> User:
        async with self.uow:
            user = await self.uow.users.get_by_email(normalize_email(email))
            if user is None:
                raise UserNotFound("user not found")

        await self._set_cache(user)
        return user

    async def update_user_profile(self, command: UpdateUserProfileCommand) -> User:
        changes = {
            field: normalize_optional(value)
            for field, value in command.changes.items()
        }

        async with self.uow:
            user = await self.uow.users.get_by_id(command.user_id)
            if user is None:
                raise UserNotFound("user not found")

            username = changes.get("username")
            if username:
                existing = await self.uow.users.get_by_username(username)
                if existing and existing.id != user.id:
                    raise UserAlreadyExists("username already exists")

            phone = changes.get("phone")
            if phone:
                existing = await self.uow.users.get_by_phone(phone)
                if existing and existing.id != user.id:
                    raise UserAlreadyExists("phone already exists")

            user.update_profile(changes)
            await self.uow.users.save(user)
            await self.uow.commit()

        await self._delete_cache(user.id)
        return user

    async def activate_user(self, command: UserIdCommand) -> User:
        async with self.uow:
            user = await self.uow.users.get_by_id(command.user_id)
            if user is None:
                raise UserNotFound("user not found")

            user.activate()
            await self.uow.users.save(user)
            await self.uow.commit()

        await self._delete_cache(user.id)
        return user

    async def enable_user(self, command: UserIdCommand) -> User:
        return await self._change_status(command.user_id, "enable")

    async def disable_user(self, command: UserIdCommand) -> User:
        return await self._change_status(command.user_id, "disable")

    async def delete_user(self, command: UserIdCommand) -> None:
        async with self.uow:
            user = await self.uow.users.get_by_id(command.user_id)
            if user is None:
                raise UserNotFound("user not found")

            user.delete()
            await self.uow.users.save(user)
            await self.uow.commit()

        await self._delete_cache(command.user_id)

    async def _change_status(self, user_id: UUID, action: str) -> User:
        async with self.uow:
            user = await self.uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFound("user not found")

            if action == "enable":
                user.enable()
            else:
                user.disable()

            await self.uow.users.save(user)
            await self.uow.commit()

        await self._delete_cache(user.id)
        return user

    async def _get_cache(self, user_id: UUID) -> User | None:
        if self.cache is None:
            return None
        try:
            return await self.cache.get_user(user_id)
        except Exception:
            return None

    async def _set_cache(self, user: User) -> None:
        if self.cache is None:
            return
        try:
            await self.cache.set_user(user)
        except Exception:
            return

    async def _delete_cache(self, user_id: UUID) -> None:
        if self.cache is None:
            return
        try:
            await self.cache.delete_user(user_id)
        except Exception:
            return

    async def _get_permission_cache(self, user_id: UUID) -> list[str] | None:
        if self.cache is None:
            return None
        try:
            return await self.cache.get_permissions(user_id)
        except Exception:
            return None

    async def _set_permission_cache(self, user_id: UUID, perms: list[str]) -> None:
        if self.cache is None:
            return
        try:
            await self.cache.set_permissions(user_id, perms, ttl=PERMISSION_CACHE_TTL)
        except Exception:
            return

    async def _delete_permission_cache(self, user_id: UUID) -> None:
        if self.cache is None:
            return
        try:
            await self.cache.delete_permissions(user_id)
        except Exception:
            return
