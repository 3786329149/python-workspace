from fastapi import APIRouter, Request, Response

from gateway.core.proxy import proxy_request
from gateway.core.routes import AUTH_ROUTE, USER_ROUTE

router = APIRouter(tags=["proxy"])

@router.api_route(
    "/auth",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
@router.api_route(
    "/auth/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_auth(request: Request, path: str = "") -> Response:
    return await proxy_request(request, AUTH_ROUTE, path)


@router.api_route(
    "/users",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
@router.api_route(
    "/users/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_users(request: Request, path: str = "") -> Response:
    return await proxy_request(request, USER_ROUTE, path)
