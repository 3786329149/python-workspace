# 系统架构概览

## 服务拓扑

```
                    ┌────────────────────────────────────────────────────┐
                    │                   Internet                         │
                    └──────────────────────┬─────────────────────────────┘
                                           │ HTTP
                    ┌──────────────────────▼─────────────────────────────┐
                    │              API Gateway (:5600)                   │
                    │  - JWT 校验（access_token）                          │
                    │  - 请求头清洗（X-User-ID / X-Internal-Token 防穿透）   │
                    │  - Rate Limiting（滑动窗口，per-IP per-service）      │
                    │  - Circuit Breaker（失败阈值熔断，自动恢复）            │
                    │  - RBAC 权限校验（Redis + user-service 回调）         │
                    │  - Request-ID 注入与传播                             │
                    │  - X-Forwarded-For 传递                             │
                    └──────┬───────────────────────────────┬─────────────┘
                           │                               │
               ┌───────────▼───────────-┐       ┌──────────▼────────────┐
               │  auth-service (:5602)  │       │ user-service (:5601)  │
               │                        │       │                       │
               │  - 注册（幂等）          │       │  - 用户 CRUD           │
               │  - 登录（风控+JWT 签发）  │       │  - RBAC：角色/权限点    │
               │  - Refresh Token 轮换   │       │  - 部门树              │
               │  - 登出/全设备登出        │◄──────│  - Redis 权限缓存      │
               │  - JWT claims 注入角色   │       │                       │
               └───────────┬───────────—┘       └──────────-┬───────────┘
                           │                                │
               ┌───────────▼──────────——┐     ┌─——──────────▼────────────┐
               │  auth_db (PostgreSQL)	│     │  user_db (PostgreSQL)  	 │
               │  user_auths          	│     │  users / departments     │
               │  refresh sessions→Redis│     │  roles / menus           │
               └──────────────────────——┘     │  user_roles / role_menus │
                                              └──────────────────——─────-┘
                           │                              │
               ┌───────────▼──────────────────────────────▼────────────┐
               │                     Redis                             │
               │  DB 1  auth-service（refresh sessions, 登录风控, 幂等键） │
               │  DB 0  user-service（user 缓存, permission 缓存）        │
               │  DB 0  gateway     （permission 缓存 L1 代理）           │
               └────────────────────────────────────────────────────────┘
```

---

## 模块职责边界

| 模块 | 职责 | 不应做的事 |
|------|------|-----------|
| **gateway** | 路由代理、JWT 校验、限流熔断、RBAC 拦截、请求头注入 | 不直接读写数据库；不存储业务状态 |
| **auth-service** | 注册/登录/登出、密码绑定、Token 签发和轮换 | 不做用户档案查询；不做 RBAC 决策 |
| **user-service** | 用户档案 CRUD、角色/权限/部门管理 | 不解析 JWT；不做登录认证 |
| **common** | 共享配置基类、DB/Redis 工厂、日志、错误类、响应格式 | 不包含业务逻辑 |

---

## 数据库设计（user_db）

```
departments                roles               menus
──────────────            ──────────────       ──────────────
id (PK)                   id (PK)              id (PK)
tenant_id                 tenant_id            parent_id → menus.id
parent_id → depts.id      name                 menu_name
name                      role_key (unique     menu_type  M/C/F
ancestors  (","分隔)       within tenant)       path
order_num                 data_scope           perms  (如 user:list)
created_at                created_at           icon / order_num
updated_at                updated_at           created_at / updated_at
deleted_at (软删)          deleted_at (软删)    deleted_at (软删)

users                     user_roles           role_menus
──────────────            ────────────         ────────────
id (PK)                   user_id → users.id   role_id → roles.id
tenant_id                 role_id → roles.id   menu_id → menus.id
email (unique)            PK(user_id,role_id)  PK(role_id,menu_id)
username (unique)
nickname / phone
avatar_url
status  PENDING/ACTIVE/DISABLED/DELETED
is_admin
dept_id → departments.id
created_at / updated_at
deleted_at (软删)
```

---

## 数据库设计（auth_db）

```
user_auths
──────────────
id (PK)
user_id (unique)      ← 对应 user_db.users.id
username (unique)
hashed_password
created_at / updated_at
deleted_at (软删)
```

---

## Redis Key 设计

| Key 模式 | 服务 | TTL | 说明 |
|---------|------|-----|------|
| `user:{user_id}` | user-service | 15 分钟 | 用户档案缓存 |
| `permission:user:{user_id}` | user-service / gateway | 5 分钟 | 权限点列表缓存 |
| `refresh:{jti}` | auth-service | 7 天 | Refresh Token session |
| `login:fail:user:{username}` | auth-service | 滑动窗口 | 登录失败次数（用户名维度） |
| `login:fail:ip:{ip}` | auth-service | 滑动窗口 | 登录失败次数（IP 维度） |
| `idempotency:{key}` | auth-service | 24 小时 | 注册幂等结果缓存 |

---

## RBAC 数据流

```
用户登录
  └─ auth-service 查询 user_roles → 写入 JWT.claims.roles[]
       （粗粒度：仅 role_key 列表，不放完整权限点，避免 Token 膨胀）

受保护路由请求
  └─ Gateway 拦截
       ├─ JWT 校验通过 → 提取 user_id
       ├─ 读取 Redis permission:user:{user_id}
       │     命中 → 直接比对路由要求的权限点
       │     未命中 → 调用 user-service GET /api/v1/users/me/permissions
       │              → 写 Redis（TTL 5 分钟）
       └─ 权限点满足 → 转发；不满足 → 403

权限变更即时生效
  └─ assign_role_to_user() → 删除 Redis permission:user:{user_id}
       下次请求自动从 DB 刷新
```

---

## 安全配置要点

```python
# ENV != "dev" 时，config 校验器强制要求：
JWT_SECRET_KEY       ≠  "change-me-*"   （至少 32 字节随机值）
INTERNAL_API_TOKEN   ≠  "change-me-*"   （至少 32 字节随机值）
```

生产部署前必须修改 `.env` 中的以上两个密钥。

---

## 本地启动顺序

```bash
# 1. 数据库迁移
uv run --package user-service alembic -c services/user_service/alembic.ini upgrade head
uv run --package auth-service  alembic -c services/auth_service/alembic.ini  upgrade head

# 2. 写入初始角色/权限种子数据（幂等，可重复执行）
uv run python scripts/seed_rbac.py

# 3. 启动服务（顺序无强依赖，但建议 user-service 先起）
uv run --package user-service python -m user_service.server   # :5601
uv run --package auth-service  python -m auth_service.server  # :5602
uv run --package gateway       python -m gateway.server       # :5600
```
