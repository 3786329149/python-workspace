from fastapi import Request
from auth_service.application.services import AuthApplicationService
from auth_service.infrastructure.db.unit_of_work import SqlAlchemyAuthUnitOfWork

def get_auth_service(request: Request) -> AuthApplicationService:
    uow = SqlAlchemyAuthUnitOfWork(request.app.state.db_session_factory)
    return AuthApplicationService(uow)
