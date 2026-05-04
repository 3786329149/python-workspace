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
| 403 | `PERMISSION_DENIED` | 无访问权限 |
| 404 | `NOT_FOUND` | 资源不存在 |
| 409 | `CONFLICT` | 资源冲突（重复注册等） |
| 422 | `UNPROCESSABLE_ENTITY` | 请求体格式错误 |
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

**Headers（可选）**
```
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
```

**Response 201**
```json
{
  "user_id": "018f1234-abcd-7000-8000-000000000001",
  "email": "user@example.com",
  "username": "alice",
  "message": "registration successful"
}
```

**错误**

| HTTP | code | 触发条件 |
|------|------|----------|
| 409 | `USER_ALREADY_EXISTS` | email 或 username 已存在 |
| 400 | `VALIDATION_ERROR` | 密码太短 / email 格式错误 |

**cURL**
```bash
curl -X POST http://localhost:5600/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"email":"user@example.com","username":"alice","password":"Str0ng!Pass"}'
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
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

> `access_token` 有效期 **30 分钟**，`refresh_token` 有效期 **7 天**。
> 前端应将 `refresh_token` 存储在 httpOnly Cookie 或安全存储中。

**错误**

| HTTP | code | 触发条件 |
|------|------|----------|
| 401 | `INVALID_CREDENTIALS` | 用户名或密码错误 |
| 429 | `LOGIN_RATE_LIMITED` | 短时间内失败次数过多 |

**cURL**
```bash
curl -X POST http://localhost:5600/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"Str0ng!Pass"}'
```

---

### 3. 刷新 Token

```
POST /api/v1/auth/refresh
```

**Request**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response 200** — 同登录，返回新的 `access_token` + `refresh_token`（旧 token 立即失效）

**错误**

| HTTP | code | 触发条件 |
|------|------|----------|
| 401 | `TOKEN_INVALID` | refresh_token 无效或已被吊销 |
| 401 | `TOKEN_EXPIRED` | refresh_token 已过期 |

**cURL**
```bash
curl -X POST http://localhost:5600/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<your_refresh_token>"}'
```

---

### 4. 登出（单设备）

```
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

**Request**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response 204** — No Content

---

### 5. 全设备登出

```
POST /api/v1/auth/logout-all
Authorization: Bearer <access_token>
```

**Request**
```json
{
  "user_id": "018f1234-abcd-7000-8000-000000000001"
}
```

**Response 204** — No Content

---

## 用户模块

### 6. 获取当前用户信息

```
GET /api/v1/users/me
Authorization: Bearer <access_token>
```

**Response 200**
```json
{
  "id": "018f1234-abcd-7000-8000-000000000001",
  "tenant_id": null,
  "email": "user@example.com",
  "username": "alice",
  "display_name": null,
  "nickname": null,
  "phone": null,
  "avatar_url": null,
  "status": "active",
  "is_admin": false,
  "dept_id": null,
  "created_at": "2026-05-04T02:00:00Z",
  "updated_at": "2026-05-04T02:00:00Z",
  "deleted_at": null
}
```

**cURL**
```bash
curl http://localhost:5600/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"
```

---

### 7. 更新用户资料

```
PATCH /api/v1/users/{user_id}
Authorization: Bearer <access_token>
```

**Request**（只传需要修改的字段）
```json
{
  "username": "alice_new",
  "nickname": "Alice",
  "phone": "13800138000",
  "avatar_url": "https://cdn.example.com/avatar.png"
}
```

**Response 200** — 返回更新后的用户对象（同 GET /users/me 格式）

**错误**

| HTTP | code | 触发条件 |
|------|------|----------|
| 409 | `USER_ALREADY_EXISTS` | username / phone 被其他用户占用 |

---

### 8. 获取当前用户权限列表

```
GET /api/v1/users/me/permissions
Authorization: Bearer <access_token>
```

**Response 200**
```json
{
  "user_id": "018f1234-abcd-7000-8000-000000000001",
  "permissions": [
    "user:list",
    "user:create",
    "role:assign"
  ]
}
```

> 结果缓存 5 分钟，角色变更后立即失效。

**cURL**
```bash
curl http://localhost:5600/api/v1/users/me/permissions \
  -H "Authorization: Bearer <access_token>"
```

---

## RBAC 模块

### 9. 创建角色

```
POST /api/v1/roles
Authorization: Bearer <access_token>
```

**Request**
```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "name": "编辑员",
  "role_key": "editor",
  "data_scope": 1
}
```

> `data_scope` 枚举：`1` 全部数据 / `2` 本部门 / `3` 本人 / `4` 自定义部门

**Response 201**
```json
{
  "id": "8074df38-a50f-4b12-a39a-2d6289aca6e5",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "name": "编辑员",
  "role_key": "editor",
  "data_scope": 1,
  "created_at": "2026-05-04T02:00:00Z",
  "updated_at": "2026-05-04T02:00:00Z"
}
```

**错误**

| HTTP | code | 触发条件 |
|------|------|----------|
| 409 | `ROLE_ALREADY_EXISTS` | 同租户下 role_key 重复 |

---

### 10. 给角色绑定权限点

```
POST /api/v1/roles/{role_id}/permissions
Authorization: Bearer <access_token>
```

**Request**
```json
{
  "menu_id": "1fe024ae-4d24-4026-a27c-052a9167f656"
}
```

**Response 204** — No Content

---

### 11. 为用户分配角色

```
POST /api/v1/users/{user_id}/roles
Authorization: Bearer <access_token>
```

**Request**
```json
{
  "role_id": "8074df38-a50f-4b12-a39a-2d6289aca6e5"
}
```

**Response 204** — No Content（同时清除该用户的权限缓存）

---

## 部门模块

### 12. 查询部门树

```
GET /api/v1/depts/tree?tenant_id={tenant_id}
Authorization: Bearer <access_token>
```

**Response 200**
```json
[
  {
    "id": "aaaaaaaa-0000-0000-0000-000000000001",
    "tenant_id": "00000000-0000-0000-0000-000000000001",
    "name": "公司",
    "parent_id": null,
    "ancestors": "",
    "order_num": 0,
    "created_at": "2026-05-04T02:00:00Z",
    "updated_at": "2026-05-04T02:00:00Z",
    "children": [
      {
        "id": "bbbbbbbb-0000-0000-0000-000000000002",
        "name": "技术部",
        "parent_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "ancestors": "aaaaaaaa-0000-0000-0000-000000000001",
        "order_num": 1,
        "children": [
          {
            "id": "cccccccc-0000-0000-0000-000000000003",
            "name": "后端组",
            "parent_id": "bbbbbbbb-0000-0000-0000-000000000002",
            "ancestors": "aaaaaaaa-...,bbbbbbbb-...",
            "children": []
          }
        ]
      }
    ]
  }
]
```

---

### 13. 创建部门

```
POST /api/v1/depts
Authorization: Bearer <access_token>
```

**Request**
```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "name": "技术部",
  "parent_id": "aaaaaaaa-0000-0000-0000-000000000001",
  "order_num": 1
}
```

> `parent_id` 为 `null` 时创建根节点。

**Response 201**
```json
{
  "id": "bbbbbbbb-0000-0000-0000-000000000002",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "name": "技术部",
  "parent_id": "aaaaaaaa-0000-0000-0000-000000000001",
  "ancestors": "aaaaaaaa-0000-0000-0000-000000000001",
  "order_num": 1,
  "created_at": "2026-05-04T02:00:00Z",
  "updated_at": "2026-05-04T02:00:00Z"
}
```

**错误**

| HTTP | code | 触发条件 |
|------|------|----------|
| 404 | `DEPT_PARENT_NOT_FOUND` | parent_id 不存在 |

---

### 14. 修改部门

```
PATCH /api/v1/depts/{dept_id}
Authorization: Bearer <access_token>
```

**Request**（只传需要修改的字段）
```json
{
  "name": "工程部",
  "order_num": 2
}
```

**Response 200** — 返回更新后的部门对象

---

### 15. 删除部门

```
DELETE /api/v1/depts/{dept_id}
Authorization: Bearer <access_token>
```

**Response 204** — No Content（软删除）

**错误**

| HTTP | code | 触发条件 |
|------|------|----------|
| 404 | `DEPT_NOT_FOUND` | 部门不存在 |
| 409 | `DEPT_HAS_CHILDREN` | 存在子部门，需先删除子部门 |

---

## 前端集成建议

### Token 管理策略

```typescript
// 推荐：access_token 存 memory，refresh_token 存 httpOnly Cookie
// 简单场景：access_token 存 localStorage，注意 XSS 风险

const ACCESS_KEY = 'access_token';

function getToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  // refresh_token 通过后端 Set-Cookie 设置更安全
}
```

### Axios 拦截器（自动刷新）

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5600',
});

// 请求拦截：注入 token
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 响应拦截：401 自动刷新
let refreshing = false;
let queue: Array<() => void> = [];

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status !== 401) return Promise.reject(error);

    const original = error.config;
    if (original._retry) {
      // 二次 401，跳转登录
      window.location.href = '/login';
      return Promise.reject(error);
    }
    original._retry = true;

    if (refreshing) {
      return new Promise((resolve) => {
        queue.push(() => resolve(api(original)));
      });
    }

    refreshing = true;
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      const { data } = await axios.post('/api/v1/auth/refresh', {
        refresh_token: refreshToken,
      });
      setTokens(data.access_token, data.refresh_token);
      queue.forEach((fn) => fn());
      queue = [];
      return api(original);
    } catch {
      window.location.href = '/login';
      return Promise.reject(error);
    } finally {
      refreshing = false;
    }
  }
);

export default api;
```

### 权限判断（前端组件层）

```typescript
// 从 GET /api/v1/users/me/permissions 获取并缓存到状态管理（如 pinia/zustand）
const permissions = ref<string[]>([]);

async function loadPermissions() {
  const { data } = await api.get('/api/v1/users/me/permissions');
  permissions.value = data.permissions;
}

function hasPermission(perm: string): boolean {
  return permissions.value.includes(perm);
}

// 使用示例
if (hasPermission('user:create')) {
  // 显示创建按钮
}
```

---

## Swagger UI（交互式测试）

服务启动后可访问：

| 服务 | Swagger UI |
|------|-----------|
| Gateway（推荐，走完整链路） | 暂无（纯代理，无文档） |
| user-service（内部直连） | http://localhost:5601/docs |
| auth-service（内部直连） | http://localhost:5602/docs |

> 提示：直连 user-service / auth-service 测试时，需手动添加 `X-Internal-Token: change-me-in-local-env` 请求头。
