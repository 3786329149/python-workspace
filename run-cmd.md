# Workspace commands

```bash
uv lock --check
```

```bash
uv run --package user-service uvicorn user_service.main:app --reload
uv run --package auth-service uvicorn auth_service.main:app --reload
```

```bash
uv run --package user-service pytest
```

```bash
uv run --package user-service alembic -c services/user_service/alembic.ini revision --autogenerate -m "message"
uv run --package user-service alembic -c services/user_service/alembic.ini upgrade head
uv run --package auth-service alembic -c services/auth_service/alembic.ini revision --autogenerate -m "message"
uv run --package auth-service alembic -c services/auth_service/alembic.ini upgrade head
```
