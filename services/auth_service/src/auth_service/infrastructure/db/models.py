from uuid import UUID

from common.database import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from auth_service.infrastructure.db.base import Base


class UserAuthRecord(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """用户授权认证表（多端登录方案）"""
    __tablename__ = "user_auths"
    __table_args__ = (
        UniqueConstraint("identity_type", "identifier", name="uq_user_auths_identity"),
    )

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, comment="用户ID")
    
    # 认证类型: 'password', 'wechat_miniapp', 'mobile'
    identity_type: Mapped[str] = mapped_column(
        String(20), 
        index=True, 
        comment="认证类型: password-密码, wechat-微信小程序, mobile-手机验证码"
    )
    
    # 标识: 账号、手机号或 微信 OpenID
    identifier: Mapped[str] = mapped_column(
        String(255), 
        index=True, 
        comment="身份标识: 账号、手机号或微信OpenID"
    )
    
    # 凭证: 密码哈希 或 微信 session_key (加密存储)
    credential: Mapped[str | None] = mapped_column(
        String(512), 
        comment="凭证: 哈希密码或第三方登录Token"
    )
