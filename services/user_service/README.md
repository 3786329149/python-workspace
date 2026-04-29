# user-service

Local configuration:

```bash
cp services/user_service/.env.example services/user_service/.env
```

FastAPI service entrypoint:

```bash
uv run --package user-service uvicorn user_service.main:app --reload
```

Run migrations:

```bash
uv run --package user-service alembic -c services/user_service/alembic.ini upgrade head
```

API v1:

```text
POST   /api/v1/users
GET    /api/v1/users/{user_id}
GET    /api/v1/users/by-email/{email}
PATCH  /api/v1/users/{user_id}
POST   /api/v1/users/{user_id}/disable
POST   /api/v1/users/{user_id}/enable
DELETE /api/v1/users/{user_id}
```
