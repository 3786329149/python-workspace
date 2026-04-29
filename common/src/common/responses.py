from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.errors import AppError
from common.logger import reset_request_id, set_request_id

REQUEST_ID_HEADER = "X-Request-ID"


def error_response(
    *,
    code: str,
    message: str,
    request_id: str,
) -> dict[str, str]:
    return {
        "code": code,
        "message": message,
        "request_id": request_id,
    }


def register_common_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        request.state.request_id = request_id
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            reset_request_id(token)

    @app.exception_handler(AppError)
    async def app_error_handler(
        request: Request,
        exc: AppError,
    ) -> JSONResponse:
        request_id = _request_id_from_request(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code=exc.code,
                message=exc.message,
                request_id=request_id,
            ),
            headers={REQUEST_ID_HEADER: request_id},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        request_id = _request_id_from_request(request)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code="HTTP_ERROR",
                message=str(exc.detail),
                request_id=request_id,
            ),
            headers={REQUEST_ID_HEADER: request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = _request_id_from_request(request)
        return JSONResponse(
            status_code=422,
            content={
                **error_response(
                    code="VALIDATION_ERROR",
                    message="request validation failed",
                    request_id=request_id,
                ),
                "details": exc.errors(),
            },
            headers={REQUEST_ID_HEADER: request_id},
        )


def _request_id_from_request(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))
