"""库存中心 - SQLAlchemy 模型"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, String, Integer, DECIMAL, DateTime, Text, Enum, 
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp_common.database import Base


class Stock(Base):
    """库存主表"""
    __tablename__ = "stock"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sku_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="SKU ID")
    warehouse_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="仓库ID")
    
    # 库存数量
    qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="实际库存数量")
    locked_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="锁定库存数量")
    available_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="可用库存数量")
    
    # 成本
    avg_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="移动加权平均成本")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    details: Mapped[list["StockDetail"]] = relationship(back_populates="stock", lazy="selectin")
    
    __table_args__ = (
        UniqueConstraint("sku_id", "warehouse_id", name="uk_sku_warehouse"),
        Index("idx_stock_sku", "sku_id"),
        Index("idx_stock_warehouse", "warehouse_id"),
    )


class StockDetail(Base):
    """库存明细表（批次库存）"""
    __tablename__ = "stock_detail"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stock.id"), nullable=False)
    sku_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="SKU ID")
    warehouse_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="仓库ID")
    
    # 批次信息
    batch_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="批次号")
    production_date: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="生产日期")
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="过期日期")
    
    # 库存数量
    qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="批次库存数量")
    locked_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="批次锁定数量")
    
    # 成本
    unit_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="批次单位成本")
    
    # 来源
    source_type: Mapped[str] = mapped_column(String(20), comment="来源类型: PURCHASE/PRODUCTION/TRANSFER")
    source_order_no: Mapped[Optional[str]] = mapped_column(String(50), comment="来源单号")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    stock: Mapped["Stock"] = relationship(back_populates="details")
    
    __table_args__ = (
        Index("idx_detail_sku", "sku_id"),
        Index("idx_detail_batch", "batch_no"),
        Index("idx_detail_stock", "stock_id"),
    )


class StockMove(Base):
    """库存流水表"""
    __tablename__ = "stock_move"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    move_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="流水号")
    sku_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="SKU ID")
    warehouse_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="仓库ID")
    
    # 流水类型
    move_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="流水类型: IN/OUT/LOCK/UNLOCK/ADJUST")
    
    # 数量变化
    qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="变动数量")
    before_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), comment="变动前数量")
    after_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), comment="变动后数量")
    
    # 成本
    unit_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="单位成本")
    
    # 来源信息
    source_type: Mapped[str] = mapped_column(String(20), comment="来源类型: PURCHASE/SALE/PRODUCTION/ADJUST")
    source_order_no: Mapped[Optional[str]] = mapped_column(String(50), comment="来源单号")
    batch_no: Mapped[Optional[str]] = mapped_column(String(50), comment="批次号")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    operator: Mapped[Optional[str]] = mapped_column(String(50), comment="操作人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_move_sku", "sku_id"),
        Index("idx_move_time", "created_at"),
        Index("idx_move_source", "source_type", "source_order_no"),
    )


class StockLock(Base):
    """库存锁定记录表"""
    __tablename__ = "stock_lock"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    lock_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="锁定单号")
    sku_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="SKU ID")
    warehouse_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="仓库ID")
    
    # 锁定数量
    locked_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="锁定数量")
    
    # 锁定状态
    status: Mapped[str] = mapped_column(String(20), default="LOCKED", comment="状态: LOCKED/UNLOCKED/CONSUMED")
    
    # 来源信息（通常是订单）
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="来源类型: ORDER/RESERVE")
    source_order_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="来源单号")
    
    # 时间戳
    locked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="锁定时间")
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="解锁时间")
    
    # 操作人
    operator: Mapped[Optional[str]] = mapped_column(String(50), comment="操作人")
    
    __table_args__ = (
        Index("idx_lock_sku", "sku_id"),
        Index("idx_lock_source", "source_type", "source_order_no"),
        Index("idx_lock_status", "status"),
    )
