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
from redis.asyncio import Redis
from common.errors import AppError
from auth_service.application.idempotency import (
    RegistrationIdempotencyManager,
    IdempotencyState,
    AuthIdempotencyConflictError,
    AuthRegistrationCompensationFailedError,
)
from auth_service.application.refresh_tokens import RefreshTokenStore, RefreshTokenSession
from auth_service.application.unit_of_work import AuthUnitOfWork
from auth_service.application.user_profiles import UserProfileClient
import time

class AuthApplicationService:
    def __init__(
        self,
        uow: AuthUnitOfWork,
        user_profiles: UserProfileClient | None = None,
        redis: Redis | None = None,
        refresh_tokens: RefreshTokenStore | None = None,
        *,
        jwt_secret_key: str = "dev-secret-change-me-with-at-least-32-bytes",
        jwt_algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ) -> None:
        self.uow = uow
        self.user_profiles = user_profiles
        self.idempotency_manager = RegistrationIdempotencyManager(redis) if redis else None
        self.refresh_tokens = refresh_tokens
        self.jwt_secret_key = jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    async def register(
        self,
        command: RegisterCommand,
        *,
        request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, str]:
        if not idempotency_key:
            raise AppError("Idempotency-Key is required", code="AUTH_IDEMPOTENCY_KEY_MISSING", status_code=428)

        if self.user_profiles is None:
            raise AuthRegistrationFailed("user profile client is not configured")

        idem_mgr = self.idempotency_manager
        if not idem_mgr:
            raise AuthRegistrationFailed("redis is required for idempotency")

        payload_hash = idem_mgr.hash_payload(command.email, command.username)
        state = await idem_mgr.get_state(idempotency_key)

        if state:
            if state.payload_hash != payload_hash:
                raise AuthIdempotencyConflictError()
            
            if state.status == "completed" and state.response:
                return state.response
            if state.status == "compensation_failed":
                raise AuthRegistrationCompensationFailedError()

        await idem_mgr.save_state(idempotency_key, IdempotencyState(status="started", payload_hash=payload_hash))

        user_data = await self.user_profiles.create_user(
            email=command.email,
            username=command.username,
            request_id=request_id,
        )
        await idem_mgr.save_state(idempotency_key, IdempotencyState(status="profile_created", payload_hash=payload_hash))

        try:
            user_id = UUID(str(user_data["id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthRegistrationFailed("user service returned invalid user id") from exc

        try:
            await self.bind_password(
                BindPasswordCommand(
                    user_id=user_id,
                    username=command.username,
                    password=command.password,
                )
            )
            await idem_mgr.save_state(idempotency_key, IdempotencyState(status="password_bound", payload_hash=payload_hash))
        except Exception as exc:
            try:
                await self.user_profiles.delete_user(user_id, request_id=request_id)
            except Exception as compensation_exc:
                await idem_mgr.save_state(idempotency_key, IdempotencyState(status="compensation_failed", payload_hash=payload_hash))
                raise AuthRegistrationCompensationFailedError() from compensation_exc
            raise exc

        try:
            await self.user_profiles.activate_user(user_id, request_id=request_id)
        except Exception as exc:
            await idem_mgr.save_state(idempotency_key, IdempotencyState(status="activation_pending", payload_hash=payload_hash))
            raise AuthRegistrationFailed("activation failed") from exc

        response = {
            "user_id": str(user_id),
            "email": str(user_data.get("email") or command.email),
            "username": str(user_data.get("username") or command.username),
            "message": "User registered successfully",
        }
        await idem_mgr.save_state(idempotency_key, IdempotencyState(status="completed", payload_hash=payload_hash, response=response))
        return response

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

        return await self._issue_tokens(auth.user_id)

    async def refresh(self, command: RefreshTokenCommand) -> dict[str, str | int]:
        payload = decode_jwt_token(
            command.refresh_token,
            secret_key=self.jwt_secret_key,
            algorithm=self.jwt_algorithm,
            expected_type=REFRESH_TOKEN_TYPE,
        )
        user_id = UUID(str(payload["sub"]))
        jti = payload.get("jti")
        
        if not jti or not self.refresh_tokens:
            raise AppError("invalid refresh token", status_code=401)
            
        session = await self.refresh_tokens.get(jti)
        if not session or session.revoked_at:
            raise AppError("refresh token revoked or invalid", status_code=401)
            
        await self.refresh_tokens.revoke(jti)
        return await self._issue_tokens(user_id)

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

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_jwt_token(
                refresh_token,
                secret_key=self.jwt_secret_key,
                algorithm=self.jwt_algorithm,
                expected_type=REFRESH_TOKEN_TYPE,
            )
        except Exception:
            return

        jti = payload.get("jti")
        if jti and self.refresh_tokens:
            await self.refresh_tokens.revoke(jti)
            
    async def logout_all(self, user_id: UUID) -> None:
        if self.refresh_tokens:
            await self.refresh_tokens.revoke_all_for_user(user_id)

    async def _issue_tokens(self, user_id: UUID) -> dict[str, str | int]:
        from uuid import uuid4
        access_expires = timedelta(minutes=self.access_token_expire_minutes)
        refresh_expires = timedelta(days=self.refresh_token_expire_days)
        subject = str(user_id)
        jti = str(uuid4())

        access_token = create_jwt_token(
            subject=subject,
            secret_key=self.jwt_secret_key,
            algorithm=self.jwt_algorithm,
            expires_delta=access_expires,
            token_type=ACCESS_TOKEN_TYPE,
        )
        refresh_token = create_jwt_token(
            subject=subject,
            secret_key=self.jwt_secret_key,
            algorithm=self.jwt_algorithm,
            expires_delta=refresh_expires,
            token_type=REFRESH_TOKEN_TYPE,
            jti=jti,
        )

        if self.refresh_tokens:
            expires_at = int(time.time() + refresh_expires.total_seconds())
            await self.refresh_tokens.save(
                jti,
                RefreshTokenSession(
                    user_id=user_id,
                    expires_at=expires_at,
                )
            )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_expires.total_seconds()),
        }
