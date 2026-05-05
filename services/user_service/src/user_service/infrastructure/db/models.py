from uuid import UUID

from common.database import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, TenantMixin
from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from user_service.domain.models import User, UserStatus, Tenant, TenantStatus
from user_service.infrastructure.db.base import Base


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", Uuid(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
)

role_menus = Table(
    "role_menus",
    Base.metadata,
    Column("role_id", Uuid(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    Column("menu_id", Uuid(as_uuid=True), ForeignKey("menus.id"), primary_key=True),
)


# 用户表
class UserRecord(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """用户主档案表"""
    __tablename__ = "users"

    # Saas 租户隔离
    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True, comment="租户ID")

    # 基础信息
    username: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, comment="用户名")
    nickname: Mapped[str | None] = mapped_column(String(64), comment="用户昵称")
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, comment="手机号")
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, comment="电子邮箱")
    avatar_url: Mapped[str | None] = mapped_column(Text, comment="头像链接")

    # 状态与标识
    status: Mapped[str] = mapped_column(String(20), default="active", index=True, comment="账号状态: active-正常, disabled-禁用, pending-待审核")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否为租户管理员: 0-否, 1-是")
    
    # 组织架构关联
    dept_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("departments.id"), index=True, comment="所属部门ID")

    @classmethod
    def from_domain(cls, user: User) -> "UserRecord":
        record = cls(id=user.id)
        record.apply(user)
        return record

    def apply(self, user: User) -> None:
        self.tenant_id = user.tenant_id
        self.username = user.username
        self.nickname = user.nickname
        self.phone = user.phone
        self.email = user.email
        self.avatar_url = user.avatar_url
        self.status = user.status.value
        self.is_admin = user.is_admin
        self.dept_id = user.dept_id
        self.created_at = user.created_at
        self.updated_at = user.updated_at
        self.deleted_at = user.deleted_at

    def to_domain(self) -> User:
        return User(
            id=self.id,
            tenant_id=self.tenant_id,
            username=self.username,
            nickname=self.nickname,
            phone=self.phone,
            email=self.email,
            avatar_url=self.avatar_url,
            status=UserStatus(self.status),
            is_admin=self.is_admin,
            dept_id=self.dept_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )


# 部门表
class DepartmentRecord(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, Base):
    """部门表"""
    __tablename__ = "departments"
    
    parent_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("departments.id"), index=True, comment="父部门ID")
    name: Mapped[str] = mapped_column(String(100), comment="部门名称")
    # 存储所有父级 ID，如 "id1,id2" 方便递归查询
    ancestors: Mapped[str | None] = mapped_column(Text, comment="祖级列表: 存储所有父级ID, 逗号分隔") 
    order_num: Mapped[int] = mapped_column(Integer, default=0, comment="显示顺序")


# 角色表
class RoleRecord(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, Base):
    """角色表"""
    __tablename__ = "roles"
    
    name: Mapped[str] = mapped_column(String(50), comment="角色名称")
   
    # 角色标识如 'admin', 'editor'
    role_key: Mapped[str] = mapped_column(String(50), index=True, comment="角色权限标识") 

    data_scope: Mapped[int] = mapped_column(Integer, 
        default=1, 
        comment="数据范围: 1-全部数据, 2-本部门数据, 3-本人数据, 4-自定义部门")
    
# 菜单与权限点表
class MenuRecord(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """菜单权限表"""
    __tablename__ = "menus"
    
    parent_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("menus.id"), index=True, comment="父菜单ID")
    menu_name: Mapped[str] = mapped_column(String(50), comment="菜单名称")
    menu_type: Mapped[str] = mapped_column(
        String(1), 
        comment="菜单类型: M-目录, C-菜单, F-按钮(权限点)"
    )
    path: Mapped[str | None] = mapped_column(String(255), comment="路由地址/API路径")
    perms: Mapped[str | None] = mapped_column(String(100), comment="权限标识: user:list")
    icon: Mapped[str | None] = mapped_column(String(100), comment="菜单图标")
    order_num: Mapped[int] = mapped_column(Integer, default=0, comment="显示顺序")


class AuditLogRecord(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """操作审计日志表"""
    __tablename__ = "audit_logs"

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, comment="操作用户ID")
    action: Mapped[str] = mapped_column(String(100), index=True, comment="操作动作")
    resource: Mapped[str] = mapped_column(String(100), comment="操作资源")
    resource_id: Mapped[str | None] = mapped_column(String(100), comment="资源ID")
    details: Mapped[str | None] = mapped_column(Text, comment="操作详情(JSON)")
    ip_address: Mapped[str | None] = mapped_column(String(45), comment="操作IP")
    status: Mapped[str] = mapped_column(String(20), default="success", comment="操作状态")


class TenantRecord(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """租户表"""
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(100), comment="租户名称")
    tenant_key: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="租户唯一标识符")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True, comment="状态")
    contact_person: Mapped[str | None] = mapped_column(String(64), comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(32), comment="联系电话")
    config: Mapped[dict] = mapped_column(JSON, default={}, comment="租户配置JSON")

    @classmethod
    def from_domain(cls, tenant: Tenant) -> "TenantRecord":
        record = cls(id=tenant.id)
        record.apply(tenant)
        return record

    def apply(self, tenant: Tenant) -> None:
        self.name = tenant.name
        self.tenant_key = tenant.tenant_key
        self.status = tenant.status.value
        self.contact_person = tenant.contact_person
        self.contact_phone = tenant.contact_phone
        self.config = tenant.config
        self.created_at = tenant.created_at
        self.updated_at = tenant.updated_at
        self.deleted_at = tenant.deleted_at

    def to_domain(self) -> Tenant:
        return Tenant(
            id=self.id,
            name=self.name,
            tenant_key=self.tenant_key,
            status=TenantStatus(self.status),
            contact_person=self.contact_person,
            contact_phone=self.contact_phone,
            config=self.config,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )

