"""订单中心 - SQLAlchemy 模型"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger, String, Integer, DECIMAL, DateTime, Text, Date,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp_common.database import Base


class SoOrder(Base):
    """销售订单主表"""
    __tablename__ = "so_order"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="订单号")
    
    # 客户信息
    customer_id: Mapped[Optional[int]] = mapped_column(BigInteger, comment="客户ID")
    customer_name: Mapped[Optional[str]] = mapped_column(String(100), comment="客户名称")
    
    # 渠道信息
    channel: Mapped[str] = mapped_column(String(20), default="ONLINE", comment="销售渠道: ONLINE/OFFLINE/POS/MOBILE")
    store_id: Mapped[Optional[int]] = mapped_column(BigInteger, comment="门店ID")
    store_name: Mapped[Optional[str]] = mapped_column(String(100), comment="门店名称")
    
    # 订单金额
    total_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="总数量")
    subtotal_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="小计金额")
    discount_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="折扣金额")
    shipping_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="运费金额")
    tax_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="税费金额")
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="总金额")
    paid_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="已付金额")
    balance_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="待付金额")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", comment="状态: DRAFT/CONFIRMED/PAYMENT_PENDING/PAYMENT_PARTIAL/PAYMENT_COMPLETED/SHIPPED/DELIVERED/CANCELLED/RETURNED")
    
    # 日期
    order_date: Mapped[datetime] = mapped_column(Date, default=date.today, comment="订单日期")
    delivery_date: Mapped[Optional[datetime]] = mapped_column(Date, comment="配送日期")
    
    # 支付信息
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), comment="支付方式")
    payment_status: Mapped[str] = mapped_column(String(20), default="PENDING", comment="支付状态: PENDING/PARTIAL/COMPLETED/FAILED")
    
    # 发货信息
    shipping_address: Mapped[Optional[str]] = mapped_column(Text, comment="收货地址")
    shipping_status: Mapped[str] = mapped_column(String(20), default="PENDING", comment="发货状态: PENDING/SHIPPED/DELIVERED")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    created_by: Mapped[Optional[str]] = mapped_column(String(50), comment="创建人")
    confirmed_by: Mapped[Optional[str]] = mapped_column(String(50), comment="确认人")
    shipped_by: Mapped[Optional[str]] = mapped_column(String(50), comment="发货人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="确认时间")
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="发货时间")
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="送达时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    details: Mapped[List["SoDetail"]] = relationship(back_populates="order", lazy="selectin", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship(back_populates="order", lazy="selectin", cascade="all, delete-orphan")
    shipments: Mapped[List["Shipment"]] = relationship(back_populates="order", lazy="selectin", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_order_no", "order_no"),
        Index("idx_customer_id", "customer_id"),
        Index("idx_channel", "channel"),
        Index("idx_store_id", "store_id"),
        Index("idx_status", "status"),
        Index("idx_order_date", "order_date"),
    )


class SoDetail(Base):
    """销售订单明细表"""
    __tablename__ = "so_detail"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("so_order.id"), nullable=False)
    
    # 商品信息
    sku_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="SKU ID")
    sku_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="SKU名称")
    barcode: Mapped[Optional[str]] = mapped_column(String(50), comment="条码")
    
    # 价格信息
    unit_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="单价")
    discount_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=0, comment="折扣率 %")
    discount_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="折扣金额")
    tax_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=0, comment="税率 %")
    tax_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="税额")
    net_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), comment="净额")
    
    # 数量信息
    qty_ordered: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="订购数量")
    qty_shipped: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="已发数量")
    qty_delivered: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="已交数量")
    qty_returned: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="退货数量")
    
    # 仓库信息
    warehouse_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="发货仓库ID")
    
    # 行号
    line_no: Mapped[int] = mapped_column(Integer, default=1, comment="行号")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(String(500), comment="备注")
    
    # 关联
    order: Mapped["SoOrder"] = relationship(back_populates="details")
    
    __table_args__ = (
        Index("idx_detail_order", "order_id"),
        Index("idx_detail_sku", "sku_id"),
        Index("idx_detail_warehouse", "warehouse_id"),
    )


class Payment(Base):
    """支付记录表"""
    __tablename__ = "payment"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    payment_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="支付单号")
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("so_order.id"), nullable=False)
    
    # 支付信息
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False, comment="支付方式")
    payment_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, comment="支付金额")
    payment_date: Mapped[datetime] = mapped_column(Date, default=date.today, comment="支付日期")
    payment_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="支付时间")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="PENDING", comment="状态: PENDING/PROCESSING/SUCCESS/FAILED/REFUNDED")
    
    # 交易信息
    transaction_id: Mapped[Optional[str]] = mapped_column(String(100), comment="交易ID")
    gateway_response: Mapped[Optional[str]] = mapped_column(Text, comment="网关响应")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    paid_by: Mapped[Optional[str]] = mapped_column(String(50), comment="支付人")
    
    # 关联
    order: Mapped["SoOrder"] = relationship(back_populates="payments")
    
    __table_args__ = (
        Index("idx_payment_no", "payment_no"),
        Index("idx_payment_order", "order_id"),
        Index("idx_payment_method", "payment_method"),
        Index("idx_payment_status", "status"),
    )


class Shipment(Base):
    """发货记录表"""
    __tablename__ = "shipment"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    shipment_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="发货单号")
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("so_order.id"), nullable=False)
    
    # 发货信息
    warehouse_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="发货仓库ID")
    shipping_company: Mapped[Optional[str]] = mapped_column(String(100), comment="物流公司")
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100), comment="物流单号")
    
    # 地址信息
    shipping_address: Mapped[Optional[str]] = mapped_column(Text, comment="收货地址")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="PENDING", comment="状态: PENDING/PICKED/SHIPPED/DELIVERED")
    
    # 日期
    shipped_date: Mapped[datetime] = mapped_column(Date, comment="发货日期")
    delivered_date: Mapped[Optional[datetime]] = mapped_column(Date, comment="送达日期")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    shipped_by: Mapped[Optional[str]] = mapped_column(String(50), comment="发货人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    order: Mapped["SoOrder"] = relationship(back_populates="shipments")
    
    __table_args__ = (
        Index("idx_shipment_no", "shipment_no"),
        Index("idx_shipment_order", "order_id"),
        Index("idx_shipment_warehouse", "warehouse_id"),
        Index("idx_shipment_status", "status"),
    )
