# auth-service

独立认证服务。负责注册、密码绑定等认证入口；只保存认证身份和凭证，不通过
ORM 外键或 relationship 直接绑定 `user_service` 的 `users` 表。

Local configuration:

```bash
cp services/auth_service/.env.example services/auth_service/.env
```

FastAPI service entrypoint:

```bash
uv run --package auth-service python -m auth_service.server
```

Default local port is `5602`; override it with `SERVICE_PORT` in
`services/auth_service/.env`.

Run migrations:

```bash
uv run --package auth-service alembic -c services/auth_service/alembic.ini upgrade head
```

当前认证表：

```text
user_auths
- user_id: user_service 用户 ID，普通 UUID 字段，不建跨服务外键
- identity_type: password / wechat / mobile 等
- identifier: 账号、手机号或第三方 openid
- credential: 密码哈希或第三方凭证
```

API v1:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/bind-password  # internal token required
```
