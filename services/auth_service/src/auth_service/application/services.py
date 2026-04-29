import bcrypt
from auth_service.domain.models import UserAuth, IdentityType
from auth_service.application.commands import BindPasswordCommand
from auth_service.application.unit_of_work import AuthUnitOfWork

class AuthApplicationService:
    def __init__(self, uow: AuthUnitOfWork) -> None:
        self.uow = uow

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
                raise ValueError("username already taken")
            
            # Check if user already has a password auth
            existing_user_auth = await self.uow.auths.get_by_user_id(
                command.user_id, IdentityType.PASSWORD
            )
            if existing_user_auth:
                raise ValueError("user already has a password bound")

            auth = UserAuth.create_password_auth(
                user_id=command.user_id,
                username=command.username,
                hashed_password=hashed_password
            )
            await self.uow.auths.add(auth)
            await self.uow.commit()
            
        return auth
