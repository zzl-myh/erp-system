"""订单中心 - Pydantic Schema"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============ 枚举类型 ============

class OrderStatus(str, Enum):
    """订单状态"""
    DRAFT = "DRAFT"                           # 草稿
    CONFIRMED = "CONFIRMED"                   # 已确认
    PAYMENT_PENDING = "PAYMENT_PENDING"       # 待支付
    PAYMENT_PARTIAL = "PAYMENT_PARTIAL"       # 部分支付
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"   # 支付完成
    SHIPPED = "SHIPPED"                       # 已发货
    DELIVERED = "DELIVERED"                   # 已送达
    CANCELLED = "CANCELLED"                   # 已取消
    RETURNED = "RETURNED"                     # 已退货


class Channel(str, Enum):
    """销售渠道"""
    ONLINE = "ONLINE"     # 线上
    OFFLINE = "OFFLINE"   # 线下
    POS = "POS"           # POS
    MOBILE = "MOBILE"     # 移动端


class PaymentStatus(str, Enum):
    """支付状态"""
    PENDING = "PENDING"     # 待支付
    PROCESSING = "PROCESSING"  # 处理中
    SUCCESS = "SUCCESS"     # 成功
    FAILED = "FAILED"       # 失败
    REFUNDED = "REFUNDED"   # 已退款


class ShippingStatus(str, Enum):
    """发货状态"""
    PENDING = "PENDING"     # 待发货
    PICKED = "PICKED"       # 已拣货
    SHIPPED = "SHIPPED"     # 已发货
    DELIVERED = "DELIVERED" # 已送达


class PaymentMethod(str, Enum):
    """支付方式"""
    CASH = "CASH"           # 现金
    CARD = "CARD"           # 银行卡
    WECHAT = "WECHAT"       # 微信
    ALIPAY = "ALIPAY"       # 支付宝
    BANK_TRANSFER = "BANK_TRANSFER"  # 银行转账
    CREDIT = "CREDIT"       # 信用额度


# ============ 订单明细 Schema ============

class SoDetailBase(BaseModel):
    """销售订单明细基础"""
    sku_id: str = Field(..., max_length=50, description="SKU ID")
    sku_name: str = Field(..., max_length=200, description="SKU名称")
    unit_price: Decimal = Field(..., ge=0, description="单价")
    qty_ordered: Decimal = Field(..., gt=0, description="订购数量")
    discount_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, description="折扣率 %")
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, description="税率 %")
    warehouse_id: int = Field(..., description="发货仓库ID")
    line_no: int = Field(default=1, description="行号")


class SoDetailCreate(SoDetailBase):
    """创建销售订单明细"""
    barcode: Optional[str] = Field(None, max_length=50, description="条码")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class SoDetailResponse(SoDetailBase):
    """销售订单明细响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    order_id: int
    barcode: Optional[str] = None
    discount_amount: Decimal
    tax_amount: Decimal
    net_amount: Decimal
    qty_shipped: Decimal
    qty_delivered: Decimal
    qty_returned: Decimal
    remark: Optional[str] = None


# ============ 订单 Schema ============

class SoOrderCreate(BaseModel):
    """创建销售订单"""
    customer_id: Optional[int] = Field(None, description="客户ID")
    customer_name: Optional[str] = Field(None, max_length=100, description="客户名称")
    channel: Channel = Field(default=Channel.POS, description="销售渠道")
    store_id: Optional[int] = Field(None, description="门店ID")
    store_name: Optional[str] = Field(None, max_length=100, description="门店名称")
    shipping_address: Optional[str] = Field(None, description="收货地址")
    payment_method: Optional[PaymentMethod] = Field(None, description="支付方式")
    remark: Optional[str] = Field(None, description="备注")
    details: List[SoDetailCreate] = Field(..., min_length=1, description="订单明细")


class SoOrderUpdate(BaseModel):
    """更新销售订单"""
    customer_id: Optional[int] = Field(None, description="客户ID")
    customer_name: Optional[str] = Field(None, max_length=100, description="客户名称")
    shipping_address: Optional[str] = Field(None, description="收货地址")
    remark: Optional[str] = Field(None, description="备注")


class SoOrderResponse(BaseModel):
    """销售订单响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    order_no: str
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    channel: str
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    total_qty: Decimal
    subtotal_amount: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    status: str
    order_date: date
    delivery_date: Optional[date] = None
    payment_method: Optional[str] = None
    payment_status: str
    shipping_address: Optional[str] = None
    shipping_status: str
    remark: Optional[str] = None
    created_by: Optional[str] = None
    confirmed_by: Optional[str] = None
    shipped_by: Optional[str] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    updated_at: datetime
    details: List[SoDetailResponse] = []


class SoOrderBrief(BaseModel):
    """销售订单简要信息"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    order_no: str
    customer_name: Optional[str] = None
    total_amount: Decimal
    status: str
    order_date: date
    created_at: datetime


# ============ 支付 Schema ============

class PaymentCreate(BaseModel):
    """创建支付记录"""
    order_id: int = Field(..., description="订单ID")
    payment_method: PaymentMethod = Field(..., description="支付方式")
    payment_amount: Decimal = Field(..., gt=0, description="支付金额")
    remark: Optional[str] = Field(None, description="备注")


class PaymentResponse(BaseModel):
    """支付记录响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    payment_no: str
    order_id: int
    payment_method: str
    payment_amount: Decimal
    payment_date: date
    payment_time: datetime
    status: str
    transaction_id: Optional[str] = None
    gateway_response: Optional[str] = None
    remark: Optional[str] = None
    paid_by: Optional[str] = None
    created_at: datetime


# ============ 发货 Schema ============

class ShipmentCreate(BaseModel):
    """创建发货记录"""
    order_id: int = Field(..., description="订单ID")
    warehouse_id: int = Field(..., description="发货仓库ID")
    shipping_company: Optional[str] = Field(None, max_length=100, description="物流公司")
    tracking_number: Optional[str] = Field(None, max_length=100, description="物流单号")
    shipping_address: Optional[str] = Field(None, description="收货地址")
    remark: Optional[str] = Field(None, description="备注")


class ShipmentResponse(BaseModel):
    """发货记录响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    shipment_no: str
    order_id: int
    warehouse_id: int
    shipping_company: Optional[str] = None
    tracking_number: Optional[str] = None
    shipping_address: Optional[str] = None
    status: str
    shipped_date: Optional[date] = None
    delivered_date: Optional[date] = None
    remark: Optional[str] = None
    shipped_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ 操作 Schema ============

class ConfirmOrderRequest(BaseModel):
    """确认订单请求"""
    pass


class CancelOrderRequest(BaseModel):
    """取消订单请求"""
    reason: Optional[str] = Field(None, max_length=500, description="取消原因")


class PayOrderRequest(BaseModel):
    """支付订单请求"""
    payment_method: PaymentMethod = Field(..., description="支付方式")
    payment_amount: Decimal = Field(..., gt=0, description="支付金额")
    remark: Optional[str] = Field(None, description="备注")


class ShipOrderRequest(BaseModel):
    """发货请求"""
    shipping_company: Optional[str] = Field(None, max_length=100, description="物流公司")
    tracking_number: Optional[str] = Field(None, max_length=100, description="物流单号")
    remark: Optional[str] = Field(None, description="备注")


# ============ 查询 Schema ============

class SoOrderQuery(BaseModel):
    """销售订单查询参数"""
    order_no: Optional[str] = Field(None, description="订单号")
    customer_id: Optional[int] = Field(None, description="客户ID")
    channel: Optional[Channel] = Field(None, description="销售渠道")
    status: Optional[OrderStatus] = Field(None, description="状态")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ============ 事件 Schema ============

class OrderCreatedEvent(BaseModel):
    """订单创建事件"""
    event_type: str = "OrderCreated"
    order_no: str
    customer_id: Optional[int] = None
    total_amount: Decimal
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderPaidEvent(BaseModel):
    """订单支付完成事件"""
    event_type: str = "OrderPaid"
    order_no: str
    payment_amount: Decimal
    payment_method: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderShippedEvent(BaseModel):
    """订单发货事件"""
    event_type: str = "OrderShipped"
    order_no: str
    shipping_company: Optional[str] = None
    tracking_number: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============ 仪表盘统计 Schema ============

class SalesTrend(BaseModel):
    """销售趋势"""
    date: str = Field(..., description="日期")
    amount: float = Field(default=0, description="销售额")
    order_count: int = Field(default=0, description="订单数")


class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    item_count: int = Field(default=0, description="商品总数")
    today_order_count: int = Field(default=0, description="今日订单数")
    member_count: int = Field(default=0, description="会员总数")
    today_sales: float = Field(default=0, description="今日销售额")
    week_sales_trend: List[SalesTrend] = Field(default=[], description="本周销售趋势")
