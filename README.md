# Python Workspace

Single-repository, multi-module FastAPI workspace managed by uv.

## Modules

- `common`: shared config, DB/session primitives, Redis, logging, errors, and response helpers.
- `services/user_service`: User profile, RBAC (roles / menus / permission-points), and department management service.
- `services/auth_service`: Authentication identity service with its own database; owns registration, credential binding, JWT issuance and refresh-token rotation.
- `gateway`: External API entry-point — JWT auth, rate limiting, circuit breaking, RBAC permission enforcement, request-ID propagation, and reverse proxy.

## Default Local Ports

```text
gateway      5600
user-service 5601
auth-service 5602
```

## Quick Start

```bash
# 1. Database migrations
uv run --package user-service alembic -c services/user_service/alembic.ini upgrade head
uv run --package auth-service  alembic -c services/auth_service/alembic.ini  upgrade head

# 2. Seed default roles and permission-points (idempotent)
uv run python scripts/seed_rbac.py

# 3. Start services
uv run --package user-service python -m user_service.server   # :5601
uv run --package auth-service  python -m auth_service.server  # :5602
uv run --package gateway       python -m gateway.server       # :5600
```

## Tests

```bash
uv run pytest -q                    # all tests
uv run pytest tests/test_rbac.py    # RBAC tests only
uv run pytest tests/test_departments.py   # Department tests
```

## Public API (no auth required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register (idempotent via `Idempotency-Key` header) |
| POST | `/api/v1/auth/login` | Login → access_token + refresh_token |
| POST | `/api/v1/auth/refresh` | Refresh token rotation |
| POST | `/api/v1/auth/logout` | Revoke refresh token |
| POST | `/api/v1/auth/logout-all` | Revoke all sessions for a user |

## Protected API (Bearer access_token required)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/users/me` | Current user profile |
| GET | `/api/v1/users/me/permissions` | Current user permission keys (Redis-cached) |
| PATCH | `/api/v1/users/{user_id}` | Update user profile |
| POST | `/api/v1/users/{user_id}/roles` | Assign role to user |
| POST | `/api/v1/roles` | Create a role |
| POST | `/api/v1/roles/{role_id}/permissions` | Bind menu/permission-point to role |
| GET | `/api/v1/depts/tree?tenant_id=` | Full dept tree (nested JSON) |
| GET | `/api/v1/depts/{dept_id}` | Single department |
| POST | `/api/v1/depts` | Create department (auto computes ancestors) |
| PATCH | `/api/v1/depts/{dept_id}` | Rename / reorder department |
| DELETE | `/api/v1/depts/{dept_id}` | Soft-delete department (409 if has children) |
| GET | `/api/v1/tenants` | Platform Admin | List all tenants |
| POST | `/api/v1/tenants` | Platform Admin | Create tenant (auto-init) |

## Environment Configuration

Each service owns its own `.env` file. Copy the `.env.example` to `.env` and fill in required values.

> **⚠️ Production requirement:** `JWT_SECRET_KEY` and `INTERNAL_API_TOKEN` must be changed to random values of at least 32 bytes. The services will refuse to start if default values are detected when `ENV != dev`.

## Further Reading

- [`docs/register-login.md`](docs/register-login.md) — Complete API call-chain reference for every business flow
- [`docs/architecture.md`](docs/architecture.md) — System architecture, DB design, Redis key design, RBAC data flow
