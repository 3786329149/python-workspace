# Python Workspace

Single-repository, multi-module FastAPI workspace managed by uv.

## Modules

- `common`: shared config, DB/session primitives, Redis, logging, errors, and response helpers.
- `services/user_service`: FastAPI user profile, organization, role, and menu service.
- `services/auth_service`: FastAPI authentication identity service with its own database; owns registration and credential flows.
- `gateway`: external API entrypoint for service routing, request-id propagation, rate limiting, circuit breaking, and timeout handling.
  Public auth routes are `/api/v1/auth/register`, `/api/v1/auth/login`, and `/api/v1/auth/refresh`; other proxied routes require a Bearer access token.

## Setup

Copy the root `.env.example` only for shared process settings. Each service
owns its own `.env.example`; copy the service example to the matching `.env`
when local overrides are needed. Gateway local overrides live in `gateway/.env`,
including `SERVICE_PORT`, rate limit, circuit breaker, timeout, and upstream URLs.

Default local ports:

```text
gateway      5600
user-service 5601
auth-service 5602
```

## Commands

```bash
uv lock --check
uv run --package user-service python -m user_service.server
uv run --package auth-service python -m auth_service.server
uv run --package gateway python -m gateway.server
uv run --package user-service pytest
uv run --package user-service alembic -c services/user_service/alembic.ini upgrade head
uv run --package auth-service alembic -c services/auth_service/alembic.ini upgrade head
```
