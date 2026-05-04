# RBAC 系统生产级加固执行计划 (Production Hardening Plan)

**当前评估状态**：基础模型已就绪，鉴权链路已打通，但缺乏自动化拦截、数据范围过滤及全局一致性保障。

---

## 🚀 第一阶段：网关与接口安全性闭环 (Security Enforcement)
- [ ] **网关权限自动化校验**
    - 在 `gateway/src/gateway/core/routes.py` 中为所有管理接口补全 `requires_permission`（如 `user:list`, `role:update`）。
    - 确保网关在转发前调用 `user-service` 的权限验证接口或直接读取 Redis 权限缓存。
- [x] **内部服务令牌 (Internal Token) 严格化**
    - 统一所有内部 `/internal/v1/*` 接口的校验逻辑。
    - 生产环境强制校验 `INTERNAL_API_TOKEN` 的长度与复杂度。
    - **已实现**: 在所有微服务的 `config.py` 中增加了生产环境 Token 长度（>=32位）校验。
- [ ] **全局错误处理规范化**
    - 统一 401 (Unauthorized) 与 403 (Forbidden) 的返回结构，确保前端能精准识别是“未登录”还是“权限不足”。

## 📊 第二阶段：数据权限与租户隔离 (Data Scope & Multi-tenancy)
- [x] **实现数据范围过滤逻辑**
    - 在 `UserApplicationService` 中解析 `Role.data_scope`。
    - 修改 `SqlAlchemyUserRepository` 和 `SqlAlchemyDepartmentRepository`，支持在查询时传入 `current_user` 的数据权限范围（例如：如果是“本人”范围，SQL 自动增加 `AND user_id = :uid`）。
    - **已实现**: 已在 Repository 层集成 `DataScope` 过滤逻辑（全部、部门、本人）。
- [x] **租户隔离加固**
    - 引入 SQLAlchemy 拦截器或 BaseRepository 封装，确保所有涉及租户的 SQL 自动带上 `WHERE tenant_id = :tid`，消除代码遗漏导致的数据越权。
    - **已实现**: 通过 `ContextVar` 维护租户上下文，并在 Repository 层强制执行 `tenant_id` 过滤。

## 🌲 第三阶段：管理后台功能补全 (Admin Feature Completion)
- [x] **菜单树结构化 API**
    - 目前 `get_all_menus` 返回的是扁平列表。需要实现 `GET /api/v1/menus/tree`，返回嵌套结构的 JSON，用于前端侧边栏渲染。
    - **已实现**: 新增了 `/menus/tree` 接口及递归组树逻辑。
- [x] **超级管理员 (Super Admin) 机制**
    - 明确 `is_admin = True` 用户的特殊逻辑（跳过权限校验），防止管理员误删自己权限导致死锁。
    - **已实现**: `get_user_permissions` 已增加 `is_admin` 自动提权逻辑。
- [ ] **角色-用户批量关联**
    - 增加批量给用户分配角色的接口，提升管理效率。

## 🛠️ 第四阶段：系统健壮性与一致性 (Robustness & Consistency)
- [x] **权限变更即时失效机制**
    - 在 `update_role_permissions` 操作时，除了更新数据库，增加逻辑：查询所有拥有该角色的 `user_id`，并批量删除 Redis 中的权限缓存 (`permission:user:{id}`)。
    - **已实现**: 在 `UserApplicationService.update_role_permissions` 中集成了批量缓存清理。
- [x] **操作审计日志 (Audit Log)**
    - 关键操作（分配角色、修改权限、禁用用户）必须记录操作人、操作时间、变更前后的内容。
    - **已实现**: 建立了 `audit_logs` 模型与仓储，并在关键 RBAC 操作中集成了审计记录逻辑。
- [ ] **完善 RBAC 集成测试**
    - 编写自动化脚本，模拟 `test01` 账号在权限变更前后的行为差异，确保逻辑无误。

---

**执行准则**：
1. **安全第一**：所有接口默认拒绝访问，除非明确配置了白名单或权限点。
2. **性能平衡**：高频鉴权逻辑必须依赖 Redis，DB 仅作为持久化兜底。
3. **原子性**：权限变更与缓存清理必须在同一个业务逻辑块中完成。
