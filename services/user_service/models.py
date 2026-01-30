"""
用户中心 - SQLAlchemy 数据模型
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp_common.database import Base


class Org(Base):
    """组织表"""
    
    __tablename__ = "org"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="组织编码")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="组织名称")
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="类型: STORE/WAREHOUSE/SUPPLIER/DEPT")
    parent_id: Mapped[int] = mapped_column(BigInteger, default=0, comment="父组织ID")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关系
    users: Mapped[List["User"]] = relationship("User", back_populates="org")


class User(Base):
    """用户表"""
    
    __tablename__ = "user"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(100), nullable=False, comment="密码哈希")
    name: Mapped[Optional[str]] = mapped_column(String(50), comment="姓名")
    mobile: Mapped[Optional[str]] = mapped_column(String(20), comment="手机号")
    email: Mapped[Optional[str]] = mapped_column(String(100), comment="邮箱")
    org_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("org.id"), comment="所属组织")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 1启用 0停用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    
    # 关系
    org: Mapped[Optional["Org"]] = relationship("Org", back_populates="users")
    roles: Mapped[List["UserRole"]] = relationship("UserRole", back_populates="user", lazy="selectin")


class Role(Base):
    """角色表"""
    
    __tablename__ = "role"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="角色编码")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="角色名称")
    description: Mapped[Optional[str]] = mapped_column(String(500), comment="描述")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Permission(Base):
    """权限表"""
    
    __tablename__ = "permission"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="权限编码")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="权限名称")
    resource: Mapped[Optional[str]] = mapped_column(String(200), comment="资源路径")
    action: Mapped[Optional[str]] = mapped_column(String(20), comment="操作: READ/WRITE/DELETE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserRole(Base):
    """用户角色关联表"""
    
    __tablename__ = "user_role"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=False)
    role_code: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关系
    user: Mapped["User"] = relationship("User", back_populates="roles")


class RolePermission(Base):
    """角色权限关联表"""
    
    __tablename__ = "role_permission"
    
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("role.id"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("permission.id"), primary_key=True)


class AuditLog(Base):
    """操作日志表"""
    
    __tablename__ = "audit_log"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="操作用户ID")
    username: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作用户名")
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作类型: CREATE/UPDATE/DELETE/LOGIN/LOGOUT")
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="资源类型: USER/ROLE/ORG")
    resource_id: Mapped[Optional[str]] = mapped_column(String(50), comment="资源ID")
    detail: Mapped[Optional[str]] = mapped_column(Text, comment="操作详情")
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), comment="IP地址")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
