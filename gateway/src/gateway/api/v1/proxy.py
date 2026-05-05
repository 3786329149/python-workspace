from fastapi import APIRouter, Request, Response

from gateway.core.proxy import proxy_request
from gateway.core.routes import AUTH_ROUTE, DEPT_ROUTE, MENU_ROUTE, ROLE_ROUTE, USER_ROUTE, TENANT_ROUTE

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


@router.api_route(
    "/roles",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
@router.api_route(
    "/roles/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_roles(request: Request, path: str = "") -> Response:
    return await proxy_request(request, ROLE_ROUTE, path)


@router.api_route(
    "/menus",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
@router.api_route(
    "/menus/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_menus(request: Request, path: str = "") -> Response:
    return await proxy_request(request, MENU_ROUTE, path)


@router.api_route(
    "/depts",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
@router.api_route(
    "/depts/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_depts(request: Request, path: str = "") -> Response:
    return await proxy_request(request, DEPT_ROUTE, path)


@router.api_route(
    "/tenants",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
@router.api_route(
    "/tenants/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_tenants(request: Request, path: str = "") -> Response:
    return await proxy_request(request, TENANT_ROUTE, path)
