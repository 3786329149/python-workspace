import bcrypt
from auth_service.domain.models import UserAuth, IdentityType
from auth_service.domain.errors import AuthAlreadyExists, AuthRegistrationFailed
from auth_service.application.commands import BindPasswordCommand, RegisterCommand
from auth_service.application.unit_of_work import AuthUnitOfWork
from auth_service.application.user_profiles import UserProfileClient
from uuid import UUID

class AuthApplicationService:
    def __init__(
        self,
        uow: AuthUnitOfWork,
        user_profiles: UserProfileClient | None = None,
    ) -> None:
        self.uow = uow
        self.user_profiles = user_profiles

    async def register(
        self,
        command: RegisterCommand,
        *,
        request_id: str | None = None,
    ) -> dict[str, str]:
        if self.user_profiles is None:
            raise AuthRegistrationFailed("user profile client is not configured")

        user_data = await self.user_profiles.create_user(
            email=command.email,
            username=command.username,
            request_id=request_id,
        )
        try:
            user_id = UUID(str(user_data["id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthRegistrationFailed(
                "user service returned invalid user id"
            ) from exc

        try:
            await self.bind_password(
                BindPasswordCommand(
                    user_id=user_id,
                    username=command.username,
                    password=command.password,
                )
            )
        except Exception as exc:
            try:
                await self.user_profiles.delete_user(user_id, request_id=request_id)
            except Exception as compensation_exc:
                raise AuthRegistrationFailed(
                    "registration failed and compensation failed"
                ) from compensation_exc
            raise exc

        return {
            "user_id": str(user_id),
            "email": str(user_data.get("email") or command.email),
            "username": str(user_data.get("username") or command.username),
            "message": "User registered successfully",
        }

    async def bind_password(self, command: BindPasswordCommand) -> UserAuth:
        # Use bcrypt directly to avoid passlib incompatibility with newer bcrypt versions
        password_bytes = command.password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        async with self.uow:
            # Check if username is already taken
            existing = await self.uow.auths.get_by_identifier(
                IdentityType.PASSWORD, command.username
            )
            if existing:
                raise AuthAlreadyExists("username already taken")
            
            # Check if user already has a password auth
            existing_user_auth = await self.uow.auths.get_by_user_id(
                command.user_id, IdentityType.PASSWORD
            )
            if existing_user_auth:
                raise AuthAlreadyExists("user already has a password bound")

            auth = UserAuth.create_password_auth(
                user_id=command.user_id,
                username=command.username,
                hashed_password=hashed_password
            )
            await self.uow.auths.add(auth)
            await self.uow.commit()
            
        return auth
