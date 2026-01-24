"""库存中心 - Pydantic Schema"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============ 枚举类型 ============

class MoveType(str, Enum):
    """流水类型"""
    IN = "IN"           # 入库
    OUT = "OUT"         # 出库
    LOCK = "LOCK"       # 锁定
    UNLOCK = "UNLOCK"   # 解锁
    ADJUST = "ADJUST"   # 调整


class SourceType(str, Enum):
    """来源类型"""
    PURCHASE = "PURCHASE"       # 采购
    SALE = "SALE"               # 销售
    PRODUCTION = "PRODUCTION"   # 生产
    TRANSFER = "TRANSFER"       # 调拨
    ADJUST = "ADJUST"           # 调整


class LockStatus(str, Enum):
    """锁定状态"""
    LOCKED = "LOCKED"       # 已锁定
    UNLOCKED = "UNLOCKED"   # 已解锁
    CONSUMED = "CONSUMED"   # 已消耗（出库）


# ============ 库存基础 Schema ============

class StockBase(BaseModel):
    """库存基础"""
    sku_id: str = Field(..., max_length=50, description="SKU ID")
    warehouse_id: int = Field(..., description="仓库ID")


class StockResponse(StockBase):
    """库存查询响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    qty: Decimal = Field(description="实际库存数量")
    locked_qty: Decimal = Field(description="锁定库存数量")
    available_qty: Decimal = Field(description="可用库存数量")
    avg_cost: Decimal = Field(description="移动加权平均成本")
    created_at: datetime
    updated_at: datetime


class StockDetailResponse(BaseModel):
    """库存明细响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    sku_id: str
    warehouse_id: int
    batch_no: str
    production_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    qty: Decimal
    locked_qty: Decimal
    unit_cost: Decimal
    source_type: str
    source_order_no: Optional[str] = None
    created_at: datetime


class StockWithDetails(StockResponse):
    """库存及明细响应"""
    details: List[StockDetailResponse] = []


# ============ 入库请求 ============

class StockInItem(BaseModel):
    """入库明细项"""
    sku_id: str = Field(..., max_length=50, description="SKU ID")
    qty: Decimal = Field(..., gt=0, description="入库数量")
    unit_cost: Decimal = Field(..., ge=0, description="单位成本")
    batch_no: Optional[str] = Field(None, max_length=50, description="批次号")
    production_date: Optional[datetime] = Field(None, description="生产日期")
    expiry_date: Optional[datetime] = Field(None, description="过期日期")


class StockInRequest(BaseModel):
    """入库请求"""
    warehouse_id: int = Field(..., description="仓库ID")
    source_type: SourceType = Field(..., description="来源类型")
    source_order_no: str = Field(..., max_length=50, description="来源单号")
    items: List[StockInItem] = Field(..., min_length=1, description="入库明细")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class StockInResponse(BaseModel):
    """入库响应"""
    success: bool = True
    move_nos: List[str] = Field(description="流水号列表")
    message: str = "入库成功"


# ============ 出库请求 ============

class StockOutItem(BaseModel):
    """出库明细项"""
    sku_id: str = Field(..., max_length=50, description="SKU ID")
    qty: Decimal = Field(..., gt=0, description="出库数量")
    batch_no: Optional[str] = Field(None, max_length=50, description="指定批次号（FIFO 自动选择）")


class StockOutRequest(BaseModel):
    """出库请求"""
    warehouse_id: int = Field(..., description="仓库ID")
    source_type: SourceType = Field(..., description="来源类型")
    source_order_no: str = Field(..., max_length=50, description="来源单号")
    items: List[StockOutItem] = Field(..., min_length=1, description="出库明细")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class StockOutResponse(BaseModel):
    """出库响应"""
    success: bool = True
    move_nos: List[str] = Field(description="流水号列表")
    total_cost: Decimal = Field(description="出库总成本")
    message: str = "出库成功"


# ============ 锁定/解锁请求 ============

class StockLockItem(BaseModel):
    """锁定明细项"""
    sku_id: str = Field(..., max_length=50, description="SKU ID")
    qty: Decimal = Field(..., gt=0, description="锁定数量")


class StockLockRequest(BaseModel):
    """库存锁定请求"""
    warehouse_id: int = Field(..., description="仓库ID")
    source_type: str = Field(default="ORDER", description="来源类型")
    source_order_no: str = Field(..., max_length=50, description="来源单号（如订单号）")
    items: List[StockLockItem] = Field(..., min_length=1, description="锁定明细")


class StockLockResponse(BaseModel):
    """锁定响应"""
    success: bool = True
    lock_nos: List[str] = Field(description="锁定单号列表")
    message: str = "锁定成功"


class StockUnlockRequest(BaseModel):
    """库存解锁请求"""
    lock_nos: Optional[List[str]] = Field(None, description="锁定单号列表（二选一）")
    source_order_no: Optional[str] = Field(None, description="来源单号（二选一）")


class StockUnlockResponse(BaseModel):
    """解锁响应"""
    success: bool = True
    unlocked_count: int = Field(description="解锁数量")
    message: str = "解锁成功"


# ============ 流水查询 ============

class StockMoveResponse(BaseModel):
    """库存流水响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    move_no: str
    sku_id: str
    warehouse_id: int
    move_type: str
    qty: Decimal
    before_qty: Decimal
    after_qty: Decimal
    unit_cost: Decimal
    source_type: str
    source_order_no: Optional[str] = None
    batch_no: Optional[str] = None
    remark: Optional[str] = None
    operator: Optional[str] = None
    created_at: datetime


class StockMoveQuery(BaseModel):
    """流水查询参数"""
    sku_id: Optional[str] = Field(None, description="SKU ID")
    warehouse_id: Optional[int] = Field(None, description="仓库ID")
    move_type: Optional[MoveType] = Field(None, description="流水类型")
    source_type: Optional[SourceType] = Field(None, description="来源类型")
    source_order_no: Optional[str] = Field(None, description="来源单号")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ============ 锁定记录查询 ============

class StockLockRecordResponse(BaseModel):
    """锁定记录响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    lock_no: str
    sku_id: str
    warehouse_id: int
    locked_qty: Decimal
    status: str
    source_type: str
    source_order_no: str
    locked_at: datetime
    unlocked_at: Optional[datetime] = None
    operator: Optional[str] = None


# ============ 库存查询 ============

class StockQuery(BaseModel):
    """库存查询参数"""
    sku_ids: Optional[List[str]] = Field(None, description="SKU ID 列表")
    warehouse_id: Optional[int] = Field(None, description="仓库ID")
    low_stock: Optional[bool] = Field(None, description="是否低库存")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ============ 库存事件 ============

class StockChangedEvent(BaseModel):
    """库存变动事件"""
    event_type: str = "StockChanged"
    sku_id: str
    warehouse_id: int
    move_type: str
    qty: Decimal
    before_qty: Decimal
    after_qty: Decimal
    source_type: str
    source_order_no: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
