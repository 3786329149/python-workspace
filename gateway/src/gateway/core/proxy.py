from urllib.parse import urljoin

import httpx
from fastapi import HTTPException, Request, Response, status

from common.responses import REQUEST_ID_HEADER
from gateway.config import settings
from gateway.core.circuit_breaker import CircuitOpen
from gateway.core.rate_limit import RateLimitExceeded
from gateway.core.routes import ServiceRoute

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


async def proxy_request(
    request: Request,
    service_route: ServiceRoute,
    path: str,
) -> Response:
    await _enforce_rate_limit(request, service_route)
    await _ensure_circuit_allows(request, service_route)

    try:
        upstream = await request.app.state.http_client.request(
            request.method,
            _upstream_url(service_route, path),
            content=await request.body(),
            headers=_proxy_headers(request, service_route),
            params=list(request.query_params.multi_items()),
        )
    except httpx.TimeoutException as exc:
        await request.app.state.circuit_breaker.record_failure(service_route.name)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"{service_route.name} timed out",
        ) from exc
    except httpx.HTTPError as exc:
        await request.app.state.circuit_breaker.record_failure(service_route.name)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{service_route.name} unavailable",
        ) from exc

    if upstream.status_code >= 500:
        await request.app.state.circuit_breaker.record_failure(service_route.name)
    else:
        await request.app.state.circuit_breaker.record_success(service_route.name)

    return _response_from_upstream(upstream)


async def _enforce_rate_limit(
    request: Request,
    service_route: ServiceRoute,
) -> None:
    try:
        await request.app.state.rate_limiter.check(
            f"{_client_id(request)}:{service_route.name}"
        )
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate limit exceeded",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc


async def _ensure_circuit_allows(
    request: Request,
    service_route: ServiceRoute,
) -> None:
    try:
        await request.app.state.circuit_breaker.before_call(service_route.name)
    except CircuitOpen as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service_route.name} circuit is open",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc


def _upstream_url(service_route: ServiceRoute, path: str) -> str:
    upstream_path = service_route.upstream_prefix.rstrip("/")
    if path:
        upstream_path = f"{upstream_path}/{path.lstrip('/')}"
    return urljoin(f"{service_route.base_url.rstrip('/')}/", upstream_path.lstrip("/"))


def _proxy_headers(request: Request, service_route: ServiceRoute) -> dict[str, str]:
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
        and key.lower() not in {"x-internal-token", "x-user-id"}
    }

    request_id = getattr(request.state, "request_id", None)
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        headers["X-User-ID"] = user_id
    if service_route.requires_internal_token:
        if not settings.INTERNAL_API_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="internal api token is not configured",
            )
        headers["X-Internal-Token"] = settings.INTERNAL_API_TOKEN

    forwarded_for = request.headers.get("x-forwarded-for")
    client_host = request.client.host if request.client else ""
    if client_host and not forwarded_for:
        headers["X-Forwarded-For"] = client_host
    headers.setdefault("X-Forwarded-Proto", request.url.scheme)
    return headers


def _response_from_upstream(upstream: httpx.Response) -> Response:
    headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=headers,
    )


def _client_id(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
