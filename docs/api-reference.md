# API Reference — 前端对接文档

> **Base URL（本地）**：`http://localhost:5600`
> 
> 所有接口统一走 **API Gateway**，前端不直接访问 auth-service / user-service。

---

## 通用约定

### 请求头

| Header | 说明 | 必填 |
|--------|------|------|
| `Content-Type` | `application/json` | POST/PATCH 必填 |
| `Authorization` | `Bearer <access_token>` | 受保护路由必填 |
| `Idempotency-Key` | UUID v4，防止重复提交 | 注册接口建议携带 |

### 响应格式

**成功** — HTTP 2xx，Body 为业务数据 JSON

**失败** — Body 统一格式：
```json
{
  "code": "ERROR_CODE",
  "message": "错误描述",
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### 通用错误码

| HTTP | code | 说明 |
|------|------|------|
| 400 | `VALIDATION_ERROR` | 请求参数校验失败 |
| 401 | `AUTH_REQUIRED` | 未携带 / 过期 token |
| 401 | `TOKEN_INVALID` | token 签名错误或类型错误 |
| 403 | `USER_PERMISSION_DENIED` | 无访问权限 |
| 404 | `NOT_FOUND` | 资源不存在 |
| 409 | `CONFLICT` | 资源冲突（重复注册等） |
| 422 | `VALIDATION_ERROR` | 请求体格式错误（含字段级详情） |
| 429 | `RATE_LIMITED` | 请求过于频繁 |
| 503 | `SERVICE_UNAVAILABLE` | 上游服务不可用 |

---

## 认证模块

### 1. 注册

```
POST /api/v1/auth/register
```

**Request**
```json
{
  "email": "user@example.com",
  "username": "alice",
  "password": "Str0ng!Pass"
}
```

**Response 201**
```json
{
  "user_id": "...",
  "email": "user@example.com",
  "username": "alice",
  "message": "registration successful"
}
```

---

### 2. 登录

```
POST /api/v1/auth/login
```

**Request**
```json
{
  "username": "alice",
  "password": "Str0ng!Pass"
}
```

**Response 200**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

> **注意**：开发环境下 `access_token` 有效期已延长至 **24 小时 (86400秒)**。

---

## 用户模块

### 3. 获取当前用户信息

```
GET /api/v1/users/me
Authorization: Bearer <access_token>
```

**Response 200**
```json
{
  "id": "...",
  "tenant_id": "...",
  "username": "alice",
  "nickname": "Alice",
  "roles": ["admin"],
  "permissions": ["user:list", "user:edit", ...],
  "status": "active",
  "is_admin": true,
  "dept_id": "..."
}
```

---

### 4. 用户管理接口

| 方法 | 路径 | 权限要求 | 说明 |
|------|------|----------|------|
| GET | `/api/v1/users` | `user:list` | 获取用户列表（受数据范围过滤） |
| GET | `/api/v1/users/{id}` | `user:list` | 获取单个用户详情（含角色与权限） |
| PATCH | `/api/v1/users/{id}` | `user:edit` | 修改基础资料（昵称、头像等） |
| PATCH | `/api/v1/users/{id}/admin` | `user:edit` | 修改核心属性（状态、部门、管理员标识） |
| DELETE | `/api/v1/users/{id}` | `user:delete` | 软删除用户 |

---

## RBAC 角色与权限

### 5. 角色管理

| 方法 | 路径 | 权限要求 | 说明 |
|------|------|----------|------|
| GET | `/api/v1/roles` | `role:list` | 获取角色列表（含该角色下的权限点列表） |
| POST | `/api/v1/roles` | `role:create` | 创建新角色（需指定 tenant_id） |
| PATCH | `/api/v1/roles/{id}` | `role:edit` | 修改角色名称、标识或数据范围 |
| PUT | `/api/v1/roles/{id}/permissions` | `role:edit` | **批量覆盖**角色的权限关联 (传 menu_ids) |
| DELETE | `/api/v1/roles/{id}` | `role:delete` | 删除角色 |

### 6. 用户角色分配

#### 批量更新用户角色
```
PUT /api/v1/users/{user_id}/roles
Authorization: Bearer <access_token>
```
**Request Body**
```json
{
  "role_ids": ["uuid-1", "uuid-2"]
}
```
> 此操作会清除用户原有的所有角色，并分配新的角色列表。权限缓存会立即失效。

---

### 7. 菜单与权限树

#### 获取扁平菜单列表
`GET /api/v1/menus`

#### 获取树状菜单结构
`GET /api/v1/menus/tree`
**Response**
```json
[
  {
    "id": "...",
    "menu_name": "系统管理",
    "menu_type": "M",
    "children": [
      {
        "id": "...",
        "menu_name": "用户管理",
        "menu_type": "C",
        "perms": "user:list",
        "children": []
      }
    ]
  }
]
```

---

## 组织架构

### 8. 部门树查询

```
GET /api/v1/depts/tree?tenant_id={tenant_id}
```

> **数据权限过滤**：非管理员用户查询时，系统会根据其角色的 `data_scope` 自动截断树结构，仅返回其有权访问的部门分支。

---

## 审计日志

### 9. 获取审计日志

```
GET /api/v1/users/audit_logs（需在网关配置路由）
```
> 目前审计日志已在后端 `audit_logs` 表记录，涵盖：分配角色、更新权限、禁用用户等敏感操作。

---

## 租户模块 (Platform Admin Only)

### 10. 创建租户

```
POST /api/v1/tenants
Authorization: Bearer <platform_admin_token>
```

**Request**
```json
{
  "name": "新客户公司",
  "tenant_key": "new_corp",
  "contact_person": "张三",
  "contact_phone": "13800000000"
}
```

**Response 201**
```json
{
  "id": "...",
  "name": "新客户公司",
  "tenant_key": "new_corp",
  "status": "active",
  "contact_person": "张三",
  "contact_phone": "13800000000",
  "config": {},
  "created_at": "...",
  "updated_at": "..."
}
```
> **注**：创建租户时，系统会自动初始化该租户的“总部”部门以及“管理员”、“普通员工”默认角色。

### 11. 获取租户列表

```
GET /api/v1/tenants
Authorization: Bearer <platform_admin_token>
```
