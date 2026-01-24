"""采购中心 - SQLAlchemy 模型"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger, String, Integer, DECIMAL, DateTime, Text, Date,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp_common.database import Base


class Supplier(Base):
    """供应商表"""
    __tablename__ = "supplier"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="供应商编码")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="供应商名称")
    short_name: Mapped[Optional[str]] = mapped_column(String(50), comment="简称")
    
    # 联系信息
    contact_person: Mapped[Optional[str]] = mapped_column(String(50), comment="联系人")
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), comment="联系电话")
    contact_email: Mapped[Optional[str]] = mapped_column(String(100), comment="邮箱")
    address: Mapped[Optional[str]] = mapped_column(String(500), comment="地址")
    
    # 财务信息
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), comment="开户银行")
    bank_account: Mapped[Optional[str]] = mapped_column(String(50), comment="银行账号")
    tax_no: Mapped[Optional[str]] = mapped_column(String(50), comment="税号")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", comment="状态: ACTIVE/INACTIVE")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    orders: Mapped[List["PoOrder"]] = relationship(back_populates="supplier", lazy="selectin")
    
    __table_args__ = (
        Index("idx_supplier_code", "code"),
        Index("idx_supplier_name", "name"),
    )


class PoOrder(Base):
    """采购订单主表"""
    __tablename__ = "po_order"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    po_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="采购单号")
    
    # 供应商
    supplier_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("supplier.id"), nullable=False)
    
    # 仓库
    warehouse_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="入库仓库")
    
    # 金额
    total_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="总数量")
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="总金额")
    tax_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="税额")
    discount_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="折扣金额")
    payable_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="应付金额")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", comment="状态: DRAFT/PENDING/APPROVED/REJECTED/RECEIVING/COMPLETED/CANCELLED")
    
    # 日期
    order_date: Mapped[datetime] = mapped_column(Date, default=datetime.utcnow, comment="订单日期")
    expected_date: Mapped[Optional[datetime]] = mapped_column(Date, comment="预计到货日期")
    
    # 审批信息
    approved_by: Mapped[Optional[str]] = mapped_column(String(50), comment="审批人")
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="审批时间")
    reject_reason: Mapped[Optional[str]] = mapped_column(String(500), comment="拒绝原因")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 创建人
    created_by: Mapped[Optional[str]] = mapped_column(String(50), comment="创建人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    supplier: Mapped["Supplier"] = relationship(back_populates="orders")
    details: Mapped[List["PoDetail"]] = relationship(back_populates="order", lazy="selectin", cascade="all, delete-orphan")
    receives: Mapped[List["PoReceive"]] = relationship(back_populates="order", lazy="selectin")
    
    __table_args__ = (
        Index("idx_po_no", "po_no"),
        Index("idx_po_supplier", "supplier_id"),
        Index("idx_po_status", "status"),
        Index("idx_po_date", "order_date"),
    )


class PoDetail(Base):
    """采购订单明细表"""
    __tablename__ = "po_detail"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    po_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("po_order.id"), nullable=False)
    
    # 商品信息
    sku_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="SKU ID")
    sku_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="SKU 名称")
    
    # 数量和价格
    qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="采购数量")
    unit_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="单价")
    tax_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=0, comment="税率 %")
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), comment="金额（不含税）")
    tax_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), comment="税额")
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), comment="含税金额")
    
    # 收货数量
    received_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="已收货数量")
    
    # 行号
    line_no: Mapped[int] = mapped_column(Integer, default=1, comment="行号")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(String(500), comment="备注")
    
    # 关联
    order: Mapped["PoOrder"] = relationship(back_populates="details")
    
    __table_args__ = (
        Index("idx_pod_po", "po_id"),
        Index("idx_pod_sku", "sku_id"),
    )


class PoReceive(Base):
    """采购收货记录表"""
    __tablename__ = "po_receive"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    receive_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="收货单号")
    po_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("po_order.id"), nullable=False)
    
    # 收货信息
    receive_date: Mapped[datetime] = mapped_column(Date, default=datetime.utcnow, comment="收货日期")
    receiver: Mapped[Optional[str]] = mapped_column(String(50), comment="收货人")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="RECEIVED", comment="状态: RECEIVED/IN_STOCK")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关联
    order: Mapped["PoOrder"] = relationship(back_populates="receives")
    details: Mapped[List["PoReceiveDetail"]] = relationship(back_populates="receive", lazy="selectin", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_receive_no", "receive_no"),
        Index("idx_receive_po", "po_id"),
    )


class PoReceiveDetail(Base):
    """采购收货明细表"""
    __tablename__ = "po_receive_detail"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    receive_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("po_receive.id"), nullable=False)
    po_detail_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("po_detail.id"), nullable=False)
    
    # 商品信息
    sku_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="SKU ID")
    
    # 收货数量
    qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="收货数量")
    unit_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="入库成本")
    
    # 批次信息
    batch_no: Mapped[Optional[str]] = mapped_column(String(50), comment="批次号")
    production_date: Mapped[Optional[datetime]] = mapped_column(Date, comment="生产日期")
    expiry_date: Mapped[Optional[datetime]] = mapped_column(Date, comment="过期日期")
    
    # 关联
    receive: Mapped["PoReceive"] = relationship(back_populates="details")
    
    __table_args__ = (
        Index("idx_rd_receive", "receive_id"),
        Index("idx_rd_sku", "sku_id"),
    )
