"""促销中心 - SQLAlchemy 模型"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger, String, Integer, DECIMAL, DateTime, Text, Date,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp_common.database import Base


class Promo(Base):
    """促销活动表"""
    __tablename__ = "promo"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="促销编码")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="促销名称")
    
    # 促销类型
    promo_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="促销类型: FULL_REDUCTION/DISCOUNT/BUY_GIFT/BUY_MORE/BUNDLE")
    
    # 适用范围
    scope_type: Mapped[str] = mapped_column(String(20), default="ALL", comment="适用范围类型: ALL/CATEGORY/SKU/BRAND")
    scope_value: Mapped[Optional[str]] = mapped_column(Text, comment="适用范围值(JSON格式)")
    
    # 促销条件
    condition_type: Mapped[str] = mapped_column(String(20), default="AMOUNT", comment="条件类型: AMOUNT/QTY")
    condition_value: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="条件值")
    
    # 促销优惠
    benefit_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="优惠类型: REDUCE/PERCENT/POINTS/GIFT")
    benefit_value: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, comment="优惠值")
    
    # 限制条件
    max_discount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="最大优惠金额")
    min_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=1, comment="最小购买数量")
    max_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="最大购买数量(0为无限制)")
    usage_limit: Mapped[int] = mapped_column(Integer, default=0, comment="使用次数限制(0为无限制)")
    
    # 有效期
    valid_from: Mapped[datetime] = mapped_column(Date, comment="有效开始日期")
    valid_to: Mapped[datetime] = mapped_column(Date, comment="有效结束日期")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", comment="状态: DRAFT/ACTIVE/INACTIVE/EXPIRED")
    
    # 优先级
    priority: Mapped[int] = mapped_column(Integer, default=1, comment="优先级(数字越大优先级越高)")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    created_by: Mapped[Optional[str]] = mapped_column(String(50), comment="创建人")
    updated_by: Mapped[Optional[str]] = mapped_column(String(50), comment="更新人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    rules: Mapped[List["PromoRule"]] = relationship(back_populates="promo", lazy="selectin", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_promo_code", "code"),
        Index("idx_promo_type", "promo_type"),
        Index("idx_status", "status"),
        Index("idx_valid_range", "valid_from", "valid_to"),
        Index("idx_priority", "priority"),
    )


class PromoRule(Base):
    """促销规则表"""
    __tablename__ = "promo_rule"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    promo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("promo.id"), nullable=False)
    
    # 规则名称
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="规则名称")
    
    # 规则条件
    condition_field: Mapped[str] = mapped_column(String(50), nullable=False, comment="条件字段")
    condition_operator: Mapped[str] = mapped_column(String(20), nullable=False, comment="条件操作符: EQ/GT/LT/GTE/LTE/IN")
    condition_value: Mapped[str] = mapped_column(Text, nullable=False, comment="条件值")
    
    # 优惠规则
    benefit_field: Mapped[str] = mapped_column(String(50), nullable=False, comment="优惠字段")
    benefit_operator: Mapped[str] = mapped_column(String(20), nullable=False, comment="优惠操作符: SET/ADD/SUB/MUL")
    benefit_value: Mapped[str] = mapped_column(Text, nullable=False, comment="优惠值")
    
    # 优先级
    priority: Mapped[int] = mapped_column(Integer, default=1, comment="优先级")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", comment="状态: ACTIVE/INACTIVE")
    
    # 关联
    promo: Mapped["Promo"] = relationship(back_populates="rules")
    
    __table_args__ = (
        Index("idx_rule_promo", "promo_id"),
        Index("idx_rule_status", "status"),
    )


class PromoRecord(Base):
    """促销应用记录表"""
    __tablename__ = "promo_record"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    promo_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="促销单号")
    promo_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="促销ID")
    promo_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="促销编码")
    promo_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="促销名称")
    
    # 应用对象
    order_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="订单号")
    sku_id: Mapped[Optional[str]] = mapped_column(String(50), comment="SKU ID")
    sku_name: Mapped[Optional[str]] = mapped_column(String(200), comment="SKU名称")
    
    # 优惠信息
    benefit_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="优惠类型")
    benefit_value: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, comment="优惠金额/折扣")
    original_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, comment="原始价格")
    final_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, comment="最终价格")
    
    # 数量信息
    qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=1, comment="数量")
    total_discount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="总优惠金额")
    
    # 应用时间
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="应用时间")
    
    # 操作人
    applied_by: Mapped[Optional[str]] = mapped_column(String(50), comment="应用人")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    __table_args__ = (
        Index("idx_promo_no", "promo_no"),
        Index("idx_promo_id", "promo_id"),
        Index("idx_order_no", "order_no"),
        Index("idx_sku_id", "sku_id"),
        Index("idx_applied_at", "applied_at"),
    )


class PromoCombination(Base):
    """促销组合表"""
    __tablename__ = "promo_combination"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="组合名称")
    
    # 组合规则
    combination_type: Mapped[str] = mapped_column(String(20), default="AND", comment="组合类型: AND/OR/SEQUENCE")
    promo_ids: Mapped[str] = mapped_column(Text, nullable=False, comment="促销ID列表(JSON格式)")
    
    # 优先级
    priority: Mapped[int] = mapped_column(Integer, default=1, comment="优先级")
    
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
        Index("idx_combo_name", "name"),
        Index("idx_combo_type", "combination_type"),
        Index("idx_combo_status", "status"),
    )
