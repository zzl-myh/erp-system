"""
领域事件定义
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """
    领域事件基类
    
    所有业务事件都应继承此类
    """
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    aggregate_id: str
    aggregate_type: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    operator: Optional[str] = None
    payload: Any = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============ 商品中心事件 ============

class ItemCreatedEvent(DomainEvent):
    """商品创建事件"""
    event_type: str = "ItemCreated"
    aggregate_type: str = "Item"


class ItemUpdatedEvent(DomainEvent):
    """商品更新事件"""
    event_type: str = "ItemUpdated"
    aggregate_type: str = "Item"


# ============ 用户中心事件 ============

class UserCreatedEvent(DomainEvent):
    """用户创建事件"""
    event_type: str = "UserCreated"
    aggregate_type: str = "User"


class UserUpdatedEvent(DomainEvent):
    """用户更新事件"""
    event_type: str = "UserUpdated"
    aggregate_type: str = "User"


# ============ 采购中心事件 ============

class PoApprovedEvent(DomainEvent):
    """采购订单审批事件"""
    event_type: str = "PoApproved"
    aggregate_type: str = "PurchaseOrder"


class PoInStockEvent(DomainEvent):
    """采购入库事件"""
    event_type: str = "PoInStock"
    aggregate_type: str = "PurchaseOrder"


# ============ 生产中心事件 ============

class MoStartedEvent(DomainEvent):
    """生产订单开始事件"""
    event_type: str = "MoStarted"
    aggregate_type: str = "ManufactureOrder"


class MoCompletedEvent(DomainEvent):
    """生产订单完工事件"""
    event_type: str = "MoCompleted"
    aggregate_type: str = "ManufactureOrder"


# ============ 报工中心事件 ============

class JobReportedEvent(DomainEvent):
    """报工事件"""
    event_type: str = "JobReported"
    aggregate_type: str = "ReportJob"


# ============ 库存中心事件 ============

class StockInEvent(DomainEvent):
    """入库事件"""
    event_type: str = "StockIn"
    aggregate_type: str = "Stock"


class StockOutEvent(DomainEvent):
    """出库事件"""
    event_type: str = "StockOut"
    aggregate_type: str = "Stock"


class StockChangedEvent(DomainEvent):
    """库存变化事件"""
    event_type: str = "StockChanged"
    aggregate_type: str = "Stock"


# ============ 成本中心事件 ============

class CostCalculatedEvent(DomainEvent):
    """成本计算完成事件"""
    event_type: str = "CostCalculated"
    aggregate_type: str = "CostSheet"


# ============ 订单中心事件 ============

class OrderPaidEvent(DomainEvent):
    """订单支付事件"""
    event_type: str = "OrderPaid"
    aggregate_type: str = "SalesOrder"


class OrderShippedEvent(DomainEvent):
    """订单发货事件"""
    event_type: str = "OrderShipped"
    aggregate_type: str = "SalesOrder"


# ============ 会员中心事件 ============

class MemberPointChangedEvent(DomainEvent):
    """会员积分变动事件"""
    event_type: str = "MemberPointChanged"
    aggregate_type: str = "Member"


# ============ 促销中心事件 ============

class PromoAppliedEvent(DomainEvent):
    """促销应用事件"""
    event_type: str = "PromoApplied"
    aggregate_type: str = "Promo"
