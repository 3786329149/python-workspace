# 认证与网关后续执行方案

## 1. 当前基线

当前主链路已经成立：

```text
注册: client -> gateway -> auth-service -> user-service -> auth-service 绑定密码
登录: client -> gateway -> auth-service 校验密码并签发 token
访问当前用户: client -> gateway 校验 JWT -> 注入 X-User-ID / X-Internal-Token -> user-service /users/me
```

当前已具备：

- gateway 做服务代理、限流、熔断、JWT 校验、`X-Request-ID` 透传。
- auth-service 拥有注册、登录、refresh token 签发接口。
- user-service 拥有 `/api/v1/users/me`，并要求内部 token 和用户上下文。
- 本地默认端口：gateway `5600`，user-service `5601`，auth-service `5602`。

当前还不适合生产上线的缺口：

- 注册缺少幂等控制。
- 用户注册缺少 `pending -> active` 状态流转。
- refresh token 还不能服务端吊销和轮换追踪。
- 登录缺少失败次数限制、账号临时锁定和审计日志。
- 内部 token 仍是共享静态密钥，缺少非 dev 环境必填校验。
- 还没有最小权限模型，只有“已登录”判断。

## 2. 总体目标

目标是把认证链路从“能跑通”推进到“可上线前验收”：

- 注册可重试、可补偿、不会因为网络重试造成脏数据。
- 登录安全可控，失败行为可限制、可审计。
- refresh token 可吊销、可轮换、可按设备或全局失效。
- gateway 只做入口治理和上下文注入，不承载注册/登录业务语义。
- user-service 只信任 gateway 注入的上下文，不直接信任客户端 header。
- 为后续 RBAC 打好 `user_id -> role -> permission` 的入口基础。

## 3. 执行阶段

### Phase 0: 先固化当前基线

优先级：P0

目标：确保当前工作区改动先被稳定保存，避免后续重构叠在未提交代码上。

任务：

- [x] 运行 `uv run pytest -q`，确认当前 31 个测试通过。
- [x] 运行 `uv lock --check`，确认锁文件一致。
- [x] 提交当前“用户上下文闭环”改动。
- [x] 保持 `.vscode/` 不进入提交，除非明确需要项目级 IDE 配置。

验收标准：

- [x] `git status --short` 只剩 `.vscode/` 或干净。
- [x] 提交信息符合 `type(scope): message(中文)`。

建议提交信息：

```text
feat(user): 完善当前用户上下文闭环
```

### Phase 1: 注册幂等与用户状态流转

优先级：P0

目标：让注册流程支持安全重试，并把用户创建过程变成明确状态机。

设计决策：

- 注册幂等由 auth-service 负责，因为 auth-service 拥有注册业务语义。
- gateway 只透传 `Idempotency-Key`，不解析注册业务。
- 幂等存储先用 Redis，TTL 默认 24 小时。
- user-service 新增内部注册资料接口，创建 `pending` 用户。
- 密码绑定成功后 auth-service 调 user-service 激活用户。
- 密码绑定失败时 auth-service 调 user-service 删除 pending 用户。

接口调整：

- auth-service:
  - [x] `POST /api/v1/auth/register` 要求 `Idempotency-Key`。
  - [x] 缺少 `Idempotency-Key` 返回 `428` 或 `400`，统一选 `428 Precondition Required`。
  - [x] 同 key 同 payload 重放，返回第一次成功响应。
  - [x] 同 key 不同 payload 返回 `409 AUTH_IDEMPOTENCY_CONFLICT`。
- user-service internal:
  - [x] `POST /internal/v1/users/registration-profile`
  - [x] `POST /internal/v1/users/{user_id}/activate`
  - [x] `DELETE /internal/v1/users/{user_id}`
  - [x] 以上接口均要求 `X-Internal-Token`。

实现任务：

- [x] user-service `User.create` 支持传入初始状态，默认仍为 `active`。
- [x] user-service 新增 application command：`CreateRegistrationProfileCommand`。
- [x] user-service 新增 internal router，独立挂载到 `/internal/v1`。
- [x] user-service internal 创建 profile 时写入 `UserStatus.PENDING`。
- [x] user-service 新增 activate 方法，只允许 `pending/disabled -> active`。
- [x] auth-service 注册 client 从公开 `/api/v1/users` 切到 user-service internal API。
- [x] auth-service 注册流程写 Redis 幂等状态：
  - `started`
  - `profile_created`
  - `password_bound`
  - `completed`
  - `compensation_failed`
- [x] auth-service 对 payload 做稳定 hash，建议字段：`email`、`username`。
- [x] 密码不要进入幂等 hash 明文日志；如必须比较请求一致性，只比较密码 hash 摘要。
- [x] auth-service 注册成功后缓存完整响应，不缓存密码。
- [x] gateway 确认代理时透传 `Idempotency-Key`。

失败处理：

- [x] 创建 pending user 失败：直接返回 user-service 错误。
- [x] 绑定密码失败：删除 pending user，返回 auth 错误。
- [x] 删除 pending user 失败：幂等状态标记 `compensation_failed`，返回 `503 AUTH_REGISTRATION_COMPENSATION_FAILED`。
- [x] 激活失败：幂等状态标记 `activation_pending`，同 key 重试只重试激活。

测试：

- [x] 注册成功：pending user -> bind password -> activate user。
- [x] 同 `Idempotency-Key` 同 payload 重放：返回缓存响应，不重复创建 user_auth。
- [x] 同 `Idempotency-Key` 不同 payload：返回 409。
- [x] bind password 失败：触发删除 pending user。
- [x] 删除 pending user 失败：返回 503，并记录可人工修复状态。
- [x] gateway 代理注册时透传 `Idempotency-Key`。

验收标准：

- [x] 注册接口能安全重试。
- [x] 数据库不会出现 active 但无密码的正常用户。
- [x] 所有新增测试通过。

### Phase 2: Refresh token 存储、轮换与登出

优先级：P0

目标：refresh token 不再只是自包含 JWT，而是服务端可追踪、可吊销。

设计决策：

- access token 继续短有效期 JWT。
- refresh token 使用 JWT + Redis session 记录。
- refresh token 每次刷新都轮换，旧 refresh token 立即失效。
- Redis key TTL 与 refresh token 过期时间一致。
- token payload 增加 `jti`。

接口调整：

- auth-service:
  - [x] `POST /api/v1/auth/refresh`
  - [x] `POST /api/v1/auth/logout`
  - [x] `POST /api/v1/auth/logout-all`

Redis key 设计：

```text
auth:refresh:{jti} -> { user_id, expires_at, revoked_at, replaced_by }
auth:user-refresh:{user_id} -> set(jti)
```

实现任务：

- [x] common security `create_jwt_token` 支持传入或生成 `jti`。
- [x] auth-service 新增 RefreshTokenStore protocol。
- [x] auth-service 新增 RedisRefreshTokenStore。
- [x] login 签发 refresh token 时写入 Redis。
- [x] refresh 时校验 JWT、校验 Redis session、轮换 refresh token。
- [x] logout 吊销当前 refresh token。
- [x] logout-all 吊销当前用户所有 refresh token。
- [x] 配置项：
  - `REFRESH_TOKEN_EXPIRE_DAYS`
  - `REFRESH_TOKEN_ROTATION_ENABLED=true`

测试：

- [x] login 后 Redis 存在 refresh jti。
- [x] refresh 成功后旧 jti 失效，新 jti 有效。
- [x] 使用旧 refresh token 再刷新返回 401。
- [x] logout 后 refresh token 不可用。
- [x] logout-all 后用户所有 refresh token 不可用。

验收标准：

- [x] 可以单设备登出。
- [x] 可以全设备登出。
- [x] refresh token 泄露后具备服务端吊销能力。

### Phase 3: 登录安全与风控基础

优先级：P1

目标：降低暴力破解、撞库和用户名枚举风险。

设计决策：

- auth-service 做用户名维度和 IP 维度的失败计数。
- gateway 继续做通用 IP 限流，但不承载登录业务判断。
- 登录失败统一返回 `AUTH_INVALID_CREDENTIALS`，不暴露用户是否存在。

配置建议：

```env
LOGIN_FAILURE_WINDOW_SECONDS=900
LOGIN_FAILURE_MAX_BY_USERNAME=5
LOGIN_FAILURE_MAX_BY_IP=30
LOGIN_LOCK_SECONDS=900
```

实现任务：

- [x] auth-service 新增 LoginAttemptLimiter protocol。
- [x] auth-service 新增 RedisLoginAttemptLimiter。
- [x] 登录前检查 username/IP 是否被锁定。
- [x] 登录失败记录计数。
- [x] 登录成功清理该 username 的失败计数。
- [x] API 层从 request 获取客户端 IP，传给 application service。
- [x] 日志记录登录成功/失败，禁止记录密码和 token。

测试：

- [x] 同 username 连续失败超过阈值后返回 429 或 423，统一选 `429`。
- [x] 同 IP 失败超过阈值后被限制。
- [x] 成功登录会清理 username 失败计数。
- [x] 不存在用户和密码错误返回相同错误码。

验收标准：

- [x] 暴力破解有基础阻断。
- [x] 不泄露用户是否存在。
- [x] 关键登录事件可通过 request_id 排查。

### Phase 4: 内部通信安全与配置校验

优先级：P1

目标：防止生产环境使用默认密钥，收紧服务间调用边界。

实现任务：

- [x] gateway 启动时校验非 dev 环境必须配置：
  - `JWT_SECRET_KEY`
  - `INTERNAL_API_TOKEN`
  - `AUTH_SERVICE_URL`
  - `USER_SERVICE_URL`
- [x] auth-service 非 dev 环境必须配置：
  - `JWT_SECRET_KEY`
  - `INTERNAL_API_TOKEN`
  - `USER_SERVICE_URL`
- [x] user-service 非 dev 环境必须配置：
  - `INTERNAL_API_TOKEN`
- [x] 禁止非 dev 使用 `change-me` 或默认 dev secret。
- [x] gateway 转发到 user-service 时始终覆盖客户端传入的：
  - `X-User-ID`
  - `X-Internal-Token`
- [x] auth-service 调 user-service internal API 时携带 `X-Internal-Token`。
- [x] 所有 internal API 缺 token 或 token 错误返回统一错误码。

测试：

- [x] prod 环境缺密钥时配置初始化失败。
- [x] 客户端伪造 `X-Internal-Token` 会被 gateway 覆盖。
- [x] user-service 直连 `/internal/v1/...` 无 token 被拒绝。
- [x] auth-service 到 user-service 的 internal 调用带 token。

验收标准：

- [x] 非 dev 环境不会静默使用弱密钥。
- [x] user-service 不接受客户端伪造身份上下文。

### Phase 5: 最小 RBAC 骨架

优先级：P2

目标：在“已登录”基础上增加“有权限”判断。

第一版范围：

- 先支持角色和权限点，不做复杂数据权限。
- gateway 只做粗粒度路由权限校验。
- user-service 管理用户角色、角色权限。
- token 内不放完整权限列表，避免权限变更后 token 长时间失真。

建议接口：

- user-service:
  - [x] `GET /api/v1/users/me/permissions`
  - [ ] `POST /api/v1/roles`（暂缓，DB 迁移时实现）
  - [ ] `POST /api/v1/roles/{role_id}/permissions`（暂缓）
  - [x] `POST /api/v1/users/{user_id}/roles`
- gateway:
  - [x] 维护路由到权限点映射（ServiceRoute.requires_permission）。
  - [x] 请求受保护路由时查询或缓存当前用户权限。

缓存策略：

- Redis key：`permission:user:{user_id}`
- TTL：5 分钟。
- 角色或权限变更后删除对应用户权限缓存。

测试：

- [x] 无权限访问受保护路由返回 403。
- [x] 有权限访问成功。
- [x] 权限变更后缓存失效。

验收标准：

- [x] 能区分登录用户是否有权访问某类接口。
- [x] 为后续菜单、按钮权限、数据权限留出扩展口。

## 4. 推荐执行顺序

严格顺序：

```text
Phase 0 -> Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5
```

如果时间紧，最低上线前必须完成：

```text
Phase 0
Phase 1 注册幂等与 pending 状态
Phase 2 refresh token 存储与登出
Phase 4 非 dev 配置校验
```

可以延后：

```text
Phase 3 登录风控增强
Phase 5 RBAC
```

## 5. 每阶段统一验收清单

每个阶段完成后都要执行：

- [ ] `uv run pytest -q`
- [ ] `uv lock --check`
- [ ] 检查 `git diff --check`
- [ ] 更新对应 `.env.example`
- [ ] 更新 README 或服务 README
- [ ] 提交信息使用 `type(scope): message(中文)`

建议提交粒度：

```text
feat(auth): 增加注册幂等与用户状态流转
feat(auth): 支持 refresh token 轮换与登出
feat(auth): 增加登录失败限制
chore(config): 强化生产环境密钥校验
feat(rbac): 增加最小权限校验骨架
```

## 6. 风险与注意事项

- 不要把注册事务放回 gateway。gateway 只做代理、鉴权、限流、熔断、上下文注入。
- 不要让 user-service 直接解析 JWT。JWT 校验集中在 gateway。
- 不要把密码、access token、refresh token 写入日志。
- 不要让客户端传入的 `X-User-ID` 或 `X-Internal-Token` 穿透到下游。
- Redis 不可用时，注册幂等和 refresh token 校验都应失败关闭，不能降级成非幂等注册或不可吊销 token。
- 非 dev 环境必须拒绝默认密钥启动。
