# SaaS 多租户架构重构审计结果与计划

## 第一阶段：项目审计结果

### 1. 核心模型设计偏差

| 模型 | 当前状态 | 目标状态 (SaaS 原则) | 风险/影响 |
| :--- | :--- | :--- | :--- |
| **User** | 包含 `tenant_id`, `dept_id`。用户被硬编码绑定到单个租户。 | 全局账号，不包含 `tenant_id`。通过 `tenant_user` 表关联组织。 | 无法支持一个用户加入多个租户，或切换租户。 |
| **Tenant** | 仅包含基础信息。 | 增加 `tenant_type` (PLATFORM/TENANT)。区分平台方和客户。 | 无法从模型层面区分“平台管理方”和“租户客户”。 |
| **Role** | 包含 `tenant_id`。 | 增加 `role_type` (PLATFORM/TENANT)。 | 平台角色和租户角色可能混用，存在安全风险。 |
| **Permission** | 在 `Menu` 中以字符串形式存在，无 scope 区分。 | 增加 `scope` (PLATFORM/TENANT/BOTH)。 | 租户可能会看到平台特有的管理菜单/功能点。 |
| **Department** | 绑定到 `tenant_id`。 | 保持不变，但需确保平台方也有自己的部门。 | 无。 |

### 2. 架构与中间件偏差

- **Context 管理**: 目前缺乏统一的 `UserContext` 和 `TenantContext`。
- **数据隔离**: `TenantMixin` 已存在，但在 Repository 层尚未实现自动化的 `tenant_id` 过滤。
- **网关鉴权**: Gateway 目前仅解析 `user_id`，未校验用户与租户的归属关系，也未区分平台入口与租户入口。
- **RBAC**: 目前的 RBAC 实现较为简单，未强制分离平台和租户的权限校验。

---

## 第二阶段：重构计划 (Phased Plan)

### 第一阶段：模型重构 (核心数据结构变更)
- **目标**: 实现 User 全局化，建立 Tenant/User 多对多关系。
- **任务**:
  1. 修改 `Tenant` 模型，添加 `tenant_type`。
  2. 创建 `tenant_users` 表 (user_id, tenant_id, dept_id, is_admin)。
  3. 修改 `Role` 模型，添加 `role_type`。
  4. 修改 `Menu/Permission` 模型，添加 `scope`。
  5. 迁移现有 `users` 表中的 `tenant_id` 和 `dept_id` 到 `tenant_users`。
- **涉及文件**: `user_service` 领域模型、数据库模型、Repository。

### 第二阶段：Context 与自动化过滤
- **目标**: 确保所有业务请求都有租户上下文，且查询自动隔离。
- **任务**:
  1. 实现 `common.context` 模块，包含 `UserContext` 和 `TenantContext`。
  2. 改造 `common.database`，在 `Session` 或 `Query` 级别注入 `tenant_id` 过滤器。
  3. 修改 Repository 基类，默认应用 `tenant_id` 过滤。
- **涉及文件**: `common` 库。

### 第三阶段：Gateway 与安全校验重构
- **目标**: 强化网关入口校验，区分平台/租户管理后台。
- **任务**:
  1. Gateway 增加路径校验：`/admin/platform/**` 仅允许 PLATFORM 类型租户的用户访问。
  2. 鉴权逻辑增加“当前活跃租户 (Active Tenant)”校验。
  3. 实现代登录 (Impersonation) 的基础逻辑（Header 传递）。
- **涉及文件**: `gateway`。

### 第四阶段：权限校验分离 (RBAC Hardening)
- **目标**: 严格分离平台权限与租户权限。
- **任务**:
  1. 修改 `PermissionService`，根据租户类型过滤可用权限。
  2. 确保角色分配时，PLATFORM 角色只能分配给 PLATFORM 租户。
  3. 改造 `check_permission` 装饰器，支持 `scope` 校验。
- **涉及文件**: `user_service` 应用层。

### 第五阶段：前端与审计配套
- **目标**: 完成闭环，包含审计日志和界面适配。
- **任务**:
  1. 改造 `AuditLog`，增加 `operator_tenant_id` (操作人所属租户) 和 `target_tenant_id` (被操作租户)，用于支持代登录审计。
  2. 调整前端路由加载逻辑，根据 `tenant_type` 加载不同的菜单。
- **涉及文件**: `user_service`, `frontend` (如果有)。

---

## 下一步行动 (Wait for Confirmation)
请确认上述审计结果和计划。确认后，我将从 **第一阶段：模型重构** 开始，首先提供数据库 Migration 方案。
