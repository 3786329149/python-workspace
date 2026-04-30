import bcrypt
from datetime import timedelta
from uuid import UUID

from common.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_jwt_token,
    decode_jwt_token,
)
from auth_service.domain.models import UserAuth, IdentityType
from auth_service.domain.errors import (
    AuthAlreadyExists,
    AuthInvalidCredentials,
    AuthRegistrationFailed,
)
from auth_service.application.commands import (
    BindPasswordCommand,
    LoginCommand,
    RefreshTokenCommand,
    RegisterCommand,
)
from auth_service.application.unit_of_work import AuthUnitOfWork
from auth_service.application.user_profiles import UserProfileClient

class AuthApplicationService:
    def __init__(
        self,
        uow: AuthUnitOfWork,
        user_profiles: UserProfileClient | None = None,
        *,
        jwt_secret_key: str = "dev-secret-change-me-with-at-least-32-bytes",
        jwt_algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ) -> None:
        self.uow = uow
        self.user_profiles = user_profiles
        self.jwt_secret_key = jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

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

    async def login(self, command: LoginCommand) -> dict[str, str | int]:
        async with self.uow:
            auth = await self.uow.auths.get_by_identifier(
                IdentityType.PASSWORD,
                command.username,
            )

        if auth is None or not auth.credential:
            raise AuthInvalidCredentials()

        try:
            password_matches = bcrypt.checkpw(
                command.password.encode("utf-8"),
                auth.credential.encode("utf-8"),
            )
        except ValueError as exc:
            raise AuthInvalidCredentials() from exc
        if not password_matches:
            raise AuthInvalidCredentials()

        return self._issue_tokens(auth.user_id)

    async def refresh(self, command: RefreshTokenCommand) -> dict[str, str | int]:
        payload = decode_jwt_token(
            command.refresh_token,
            secret_key=self.jwt_secret_key,
            algorithm=self.jwt_algorithm,
            expected_type=REFRESH_TOKEN_TYPE,
        )
        return self._issue_tokens(UUID(str(payload["sub"])))

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

    def _issue_tokens(self, user_id: UUID) -> dict[str, str | int]:
        access_expires = timedelta(minutes=self.access_token_expire_minutes)
        refresh_expires = timedelta(days=self.refresh_token_expire_days)
        subject = str(user_id)

        return {
            "access_token": create_jwt_token(
                subject=subject,
                secret_key=self.jwt_secret_key,
                algorithm=self.jwt_algorithm,
                expires_delta=access_expires,
                token_type=ACCESS_TOKEN_TYPE,
            ),
            "refresh_token": create_jwt_token(
                subject=subject,
                secret_key=self.jwt_secret_key,
                algorithm=self.jwt_algorithm,
                expires_delta=refresh_expires,
                token_type=REFRESH_TOKEN_TYPE,
            ),
            "token_type": "bearer",
            "expires_in": int(access_expires.total_seconds()),
        }
