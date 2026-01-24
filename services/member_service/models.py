"""会员中心 - SQLAlchemy 模型"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger, String, Integer, DECIMAL, DateTime, Text, Date,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp_common.database import Base


class Member(Base):
    """会员表"""
    __tablename__ = "member"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    member_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="会员号")
    
    # 基本信息
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, comment="手机号")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="姓名")
    gender: Mapped[Optional[str]] = mapped_column(String(10), comment="性别: M/F")
    birthday: Mapped[Optional[datetime]] = mapped_column(Date, comment="生日")
    email: Mapped[Optional[str]] = mapped_column(String(100), comment="邮箱")
    
    # 会员等级
    level_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="会员等级ID")
    level_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="会员等级名称")
    points: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="积分")
    total_consumed: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="累计消费金额")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", comment="状态: ACTIVE/INACTIVE/BANNED")
    
    # 推荐人
    referee_id: Mapped[Optional[int]] = mapped_column(BigInteger, comment="推荐人ID")
    referee_name: Mapped[Optional[str]] = mapped_column(String(50), comment="推荐人姓名")
    
    # 注册信息
    register_channel: Mapped[str] = mapped_column(String(20), default="ONLINE", comment="注册渠道")
    register_store: Mapped[Optional[str]] = mapped_column(String(50), comment="注册门店")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    created_by: Mapped[Optional[str]] = mapped_column(String(50), comment="创建人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_member_no", "member_no"),
        Index("idx_phone", "phone"),
        Index("idx_level", "level_id"),
        Index("idx_status", "status"),
        Index("idx_created_at", "created_at"),
    )


class MemberLevel(Base):
    """会员等级表"""
    __tablename__ = "member_level"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, comment="等级编码")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="等级名称")
    
    # 等级权益
    discount_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=100, comment="折扣率 %")
    points_multiplier: Mapped[Decimal] = mapped_column(DECIMAL(3, 2), default=1.0, comment="积分倍数")
    
    # 升级条件
    min_points: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="最低积分")
    min_consumed: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="最低消费金额")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", comment="状态: ACTIVE/INACTIVE")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    created_by: Mapped[Optional[str]] = mapped_column(String(50), comment="创建人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_level_code", "code"),
        Index("idx_level_name", "name"),
        Index("idx_min_points", "min_points"),
        Index("idx_min_consumed", "min_consumed"),
    )


class MemberPoint(Base):
    """会员积分记录表"""
    __tablename__ = "member_point"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="会员ID")
    member_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="会员号")
    
    # 积分变动
    change_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="变动类型: EARN/CONSUME/EXPIRE/ADJUST")
    change_points: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, comment="变动积分数")
    balance_before: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, comment="变动前余额")
    balance_after: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, comment="变动后余额")
    
    # 来源单据
    source_type: Mapped[str] = mapped_column(String(20), comment="来源类型: ORDER/RECHARGE/PROMOTION/ADJUST")
    source_no: Mapped[Optional[str]] = mapped_column(String(50), comment="来源单号")
    
    # 有效期
    expire_date: Mapped[Optional[datetime]] = mapped_column(Date, comment="过期日期")
    expired_points: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="过期积分数")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    operator: Mapped[Optional[str]] = mapped_column(String(50), comment="操作人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_member_id", "member_id"),
        Index("idx_member_no", "member_no"),
        Index("idx_change_type", "change_type"),
        Index("idx_source", "source_type", "source_no"),
        Index("idx_expire_date", "expire_date"),
    )


class MemberCoupon(Base):
    """会员优惠券表"""
    __tablename__ = "member_coupon"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    coupon_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="优惠券编号")
    member_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="会员ID")
    member_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="会员号")
    
    # 优惠券信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="优惠券名称")
    coupon_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="优惠券类型: DISCOUNT/CASH/EXCHANGE")
    value: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, comment="优惠券面值")
    min_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="最低使用金额")
    
    # 有效期
    valid_from: Mapped[datetime] = mapped_column(Date, comment="有效开始日期")
    valid_to: Mapped[datetime] = mapped_column(Date, comment="有效结束日期")
    
    # 使用限制
    usage_limit: Mapped[int] = mapped_column(Integer, default=1, comment="使用次数限制")
    used_count: Mapped[int] = mapped_column(Integer, default=0, comment="已使用次数")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="UNUSED", comment="状态: UNUSED/USED/EXPIRED/CANCELLED")
    
    # 来源
    source_type: Mapped[str] = mapped_column(String(20), comment="来源类型")
    source_no: Mapped[Optional[str]] = mapped_column(String(50), comment="来源单号")
    
    # 使用信息
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="使用时间")
    used_order_no: Mapped[Optional[str]] = mapped_column(String(50), comment="使用订单号")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    issued_by: Mapped[Optional[str]] = mapped_column(String(50), comment="发放人")
    used_by: Mapped[Optional[str]] = mapped_column(String(50), comment="使用人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_coupon_no", "coupon_no"),
        Index("idx_member_id", "member_id"),
        Index("idx_member_no", "member_no"),
        Index("idx_status", "status"),
        Index("idx_valid_to", "valid_to"),
    )
