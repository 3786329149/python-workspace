# Python Workspace

Single-repository, multi-module FastAPI workspace managed by uv.

## Modules

- `common`: shared config, DB/session primitives, Redis, logging, errors, and response helpers.
- `services/user_service`: FastAPI user profile, organization, role, and menu service.
- `services/auth_service`: FastAPI authentication identity service with its own database.
- `gateway`: reserved placeholder.

## Setup

Copy the root `.env.example` only for shared process settings. Each service
owns its own `.env.example`; copy the service example to the matching `.env`
when local DB or Redis overrides are needed.

## Commands

```bash
uv lock --check
uv run --package user-service python -m user_service.server
uv run --package auth-service python -m auth_service.server
uv run --package user-service pytest
uv run --package user-service alembic -c services/user_service/alembic.ini upgrade head
uv run --package auth-service alembic -c services/auth_service/alembic.ini upgrade head
```
