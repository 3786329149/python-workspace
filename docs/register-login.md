# API 调用链路文档

> 描述各业务场景下，客户端→网关→微服务的完整请求链路。

---

## 1. 注册

```
POST /api/v1/auth/register
Header: Idempotency-Key: <uuid>
Body: { email, username, password }
```

```text
Client
  → Gateway  POST /api/v1/auth/register
      ├─ 不校验 JWT（公开路由）
      └─ 转发到 auth-service POST /api/v1/auth/register

auth-service（注册事务）
  1. 检查 Idempotency-Key（Redis），防重复提交
  2. → user-service POST /internal/v1/users/registration-profile  创建 PENDING 用户
  3.   绑定密码（bcrypt hash 存 user_auths 表）
  4. → user-service POST /internal/v1/users/{user_id}/activate   激活用户
  5. 将幂等结果写入 Redis
  6. 返回 { user_id, email, username, message }

注意：任一步骤失败均触发补偿（删除已创建用户），保证最终一致性。
```

---

## 2. 登录

```
POST /api/v1/auth/login
Body: { username, password }
```

```text
Client
  → Gateway  POST /api/v1/auth/login
      ├─ 不校验 JWT（公开路由）
      └─ 转发到 auth-service POST /api/v1/auth/login

auth-service（登录流程）
  1. 登录风控前置检查（RedisLoginAttemptLimiter）
     ├─ 按 username 维度：滑动窗口计数，超限返回 429
     └─ 按 client_ip 维度：同上
  2. 查询 user_auths 表（username → hashed_password）
  3. bcrypt 校验密码
  4. 密码正确 → 清空失败计数；密码错误 → 记录失败次数
  5. 从 user_service 读取用户角色 → 写入 JWT claims（roles[]）
  6. 签发 access_token（JWT, 30 分钟）+ refresh_token（JWT+jti, 7 天）
  7. refresh_token session 存 Redis（key: refresh:{jti}）
  8. 返回 { access_token, refresh_token, token_type, expires_in }
```

---

## 3. 刷新 Token

```
POST /api/v1/auth/refresh
Body: { refresh_token }
```

```text
Client
  → Gateway  POST /api/v1/auth/refresh
      ├─ 不校验 JWT（公开路由）
      └─ 转发到 auth-service POST /api/v1/auth/refresh

auth-service（Token 轮换）
  1. 解码 refresh_token，验证签名和 token_type
  2. 从 Redis 查询 refresh session（key: refresh:{jti}）
  3. 检查 session 是否已被吊销（revoked_at）
  4. 吊销旧 jti
  5. 重新查询用户角色
  6. 签发全新 access_token + refresh_token（新 jti）
  7. 返回新 token 对
```

---

## 4. 登出

```
POST /api/v1/auth/logout
Body: { refresh_token }
```

```text
auth-service
  1. 解码 refresh_token（容忍解码失败，静默返回）
  2. 从 Redis 中吊销该 jti 的 session
  → 204 No Content
```

---

## 5. 全设备登出

```
POST /api/v1/auth/logout-all
Body: { user_id }
Header: Authorization: Bearer <access_token>
```

```text
auth-service
  1. 扫描并吊销该 user_id 下所有 refresh session
  → 204 No Content
```

---

## 6. 访问当前用户信息

```
GET /api/v1/users/me
Header: Authorization: Bearer <access_token>
```

```text
Client
  → Gateway  GET /api/v1/users/me
      ├─ 校验 JWT（解码、验签、检查 token_type=access）
      ├─ 提取 sub → user_id 存入 request.state
      ├─ 清洗请求头（移除客户端伪造的 X-User-ID / X-Internal-Token）
      ├─ 注入 X-User-ID: <user_id>
      ├─ 注入 X-Internal-Token: <INTERNAL_API_TOKEN>
      └─ 转发到 user-service GET /api/v1/users/me

user-service
  1. 校验 X-Internal-Token
  2. 从 X-User-ID 提取 user_id
  3. 先查 Redis 缓存（key: user:{user_id}，TTL 15 分钟）
  4. Cache miss → 查 PostgreSQL users 表
  5. 回写缓存
  6. 返回用户完整资料
```

---

## 7. 查询当前用户权限

```
GET /api/v1/users/me/permissions
Header: Authorization: Bearer <access_token>
```

```text
Client
  → Gateway（注入 X-User-ID + X-Internal-Token）
  → user-service GET /api/v1/users/me/permissions

user-service
  1. 先查 Redis 缓存（key: permission:user:{user_id}，TTL 5 分钟）
  2. Cache miss → 联表查询 user_roles → roles → role_menus → menus
     过滤条件：menu_type = 'F'（权限点）且 perms 非空
  3. 去重排序后回写缓存
  4. 返回 { user_id, permissions: ["user:list", "role:assign", ...] }
```

---

## 8. 为用户分配角色

```
POST /api/v1/users/{user_id}/roles
Header: Authorization: Bearer <access_token>
Body: { role_id }
```

```text
user-service
  1. 校验 user_id 存在
  2. 校验 role_id 存在
  3. INSERT INTO user_roles（ON CONFLICT DO NOTHING）
  4. 删除 Redis 权限缓存（key: permission:user:{user_id}）
  → 204 No Content
```

---

## 9. 创建角色

```
POST /api/v1/roles
Header: Authorization: Bearer <access_token>
Body: { tenant_id, name, role_key, data_scope }
```

```text
user-service
  1. 检查同租户下 role_key 唯一（重复返回 409）
  2. INSERT INTO roles
  3. 返回 { id, tenant_id, name, role_key, data_scope, created_at, updated_at }
```

---

## 10. 给角色绑定权限点

```
POST /api/v1/roles/{role_id}/permissions
Header: Authorization: Bearer <access_token>
Body: { menu_id }
```

```text
user-service
  1. 校验 role_id 存在
  2. INSERT INTO role_menus（ON CONFLICT DO NOTHING）
  3. 权限缓存自然 5 分钟后过期
  → 204 No Content
```

---

## 11. 部门树查询

```
GET /api/v1/depts/tree?tenant_id={tenant_id}
Header: Authorization: Bearer <access_token>
```

```text
user-service
  1. 查询该租户下所有未删除部门（按 order_num 排序）
  2. 在内存中组装树结构（O(n) 算法，利用 ancestors 路径）
  3. 返回嵌套 JSON 树（根节点列表，每个节点含 children）
```

---

## 12. 创建部门

```
POST /api/v1/depts
Header: Authorization: Bearer <access_token>
Body: { tenant_id, name, parent_id?, order_num? }
```

```text
user-service
  1. 若指定 parent_id → 查询父部门，获取 ancestors 路径
  2. 子部门 ancestors = parent.ancestors + "," + parent.id
  3. INSERT INTO departments
  4. 返回部门详情（含 ancestors 字段）
```

---

## 安全机制汇总

| 机制 | 实现位置 | 说明 |
|------|---------|------|
| JWT 签名校验 | Gateway 中间件 | 所有非公开路由强制校验 |
| 登录暴力破解防护 | auth-service（Redis） | username + IP 双维度滑动窗口，超限 429 |
| 内部服务鉴权 | X-Internal-Token | 网关注入，下游校验，防止客户端伪造 |
| 请求头清洗 | Gateway proxy | 代理前移除 X-User-ID / X-Internal-Token |
| Refresh Token 轮换 | auth-service（Redis） | 每次刷新吊销旧 jti，防止 Token 重放 |
| 权限点校验（RBAC） | Gateway + user-service | Redis 缓存权限点，5 分钟 TTL |
| 幂等注册 | auth-service（Redis） | Idempotency-Key 防止网络重试造成重复注册 |
| 生产环境配置校验 | 各服务 config.py | ENV != dev 时强制要求非默认密钥 |
