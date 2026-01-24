"""生产中心 - Pydantic Schema"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============ 枚举类型 ============

class MoStatus(str, Enum):
    """生产订单状态"""
    DRAFT = "DRAFT"           # 草稿
    RELEASED = "RELEASED"     # 已下达
    STARTED = "STARTED"       # 已开工
    PAUSED = "PAUSED"         # 已暂停
    COMPLETED = "COMPLETED"   # 已完成
    CANCELLED = "CANCELLED"   # 已取消


class BomStatus(str, Enum):
    """BOM状态"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RoutingStatus(str, Enum):
    """工序状态"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


# ============ BOM Schema ============

class BomTemplateBase(BaseModel):
    """BOM模板基础"""
    code: str = Field(..., max_length=50, description="BOM编码")
    name: str = Field(..., max_length=200, description="BOM名称")
    product_sku_id: str = Field(..., max_length=50, description="成品SKU ID")
    product_sku_name: str = Field(..., max_length=200, description="成品SKU名称")
    version: str = Field(default="V1.0", max_length=20, description="版本号")


class BomTemplateItemBase(BaseModel):
    """BOM明细基础"""
    material_sku_id: str = Field(..., max_length=50, description="物料SKU ID")
    material_sku_name: str = Field(..., max_length=200, description="物料SKU名称")
    qty: Decimal = Field(..., gt=0, description="需求数量")
    unit: Optional[str] = Field(None, max_length=20, description="单位")
    line_no: int = Field(default=1, description="行号")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class BomTemplateItemCreate(BomTemplateItemBase):
    """创建BOM明细"""
    pass


class BomTemplateItemResponse(BomTemplateItemBase):
    """BOM明细响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    bom_id: int


class BomTemplateCreate(BomTemplateBase):
    """创建BOM模板"""
    items: List[BomTemplateItemCreate] = Field(..., min_length=1, description="BOM明细")
    valid_from: date = Field(..., description="生效日期")
    valid_to: Optional[date] = Field(None, description="失效日期")
    remark: Optional[str] = Field(None, description="备注")


class BomTemplateUpdate(BaseModel):
    """更新BOM模板"""
    name: Optional[str] = Field(None, max_length=200)
    version: Optional[str] = Field(None, max_length=20)
    valid_from: Optional[date] = Field(None, description="生效日期")
    valid_to: Optional[date] = Field(None, description="失效日期")
    status: Optional[BomStatus] = None
    remark: Optional[str] = None


class BomTemplateResponse(BomTemplateBase):
    """BOM模板响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    revision: int
    status: str
    valid_from: date
    valid_to: Optional[date] = None
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[BomTemplateItemResponse] = []


# ============ 生产订单 Schema ============

class MoDetailBase(BaseModel):
    """生产明细基础"""
    material_sku_id: str = Field(..., max_length=50, description="物料SKU ID")
    material_sku_name: str = Field(..., max_length=200, description="物料SKU名称")
    required_qty: Decimal = Field(..., gt=0, description="需求数量")
    unit: Optional[str] = Field(None, max_length=20, description="单位")
    line_no: int = Field(default=1, description="行号")


class MoDetailResponse(MoDetailBase):
    """生产明细响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    mo_id: int
    issued_qty: Decimal
    consumed_qty: Decimal


class MoRoutingBase(BaseModel):
    """工序基础"""
    operation_no: str = Field(..., max_length=20, description="工序编号")
    operation_name: str = Field(..., max_length=100, description="工序名称")
    description: Optional[str] = Field(None, max_length=500, description="工序描述")
    planned_hours: Optional[Decimal] = Field(None, ge=0, description="计划工时")
    priority: int = Field(default=1, description="优先级")


class MoRoutingResponse(MoRoutingBase):
    """工序响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    mo_id: int
    status: str
    planned_start_time: Optional[datetime] = None
    planned_end_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None


class MoOrderCreate(BaseModel):
    """创建生产订单"""
    product_sku_id: str = Field(..., max_length=50, description="成品SKU ID")
    product_sku_name: str = Field(..., max_length=200, description="成品SKU名称")
    planned_qty: Decimal = Field(..., gt=0, description="计划生产数量")
    bom_id: int = Field(..., description="BOM模板ID")
    warehouse_id: int = Field(..., description="生产仓库ID")
    raw_material_warehouse_id: int = Field(..., description="原料仓库ID")
    planned_start_date: date = Field(..., description="计划开工日期")
    planned_end_date: date = Field(..., description="计划完工日期")
    remark: Optional[str] = Field(None, description="备注")


class MoOrderUpdate(BaseModel):
    """更新生产订单"""
    planned_start_date: Optional[date] = Field(None, description="计划开工日期")
    planned_end_date: Optional[date] = Field(None, description="计划完工日期")
    remark: Optional[str] = None


class MoOrderResponse(BaseModel):
    """生产订单响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    mo_no: str
    product_sku_id: str
    product_sku_name: str
    planned_qty: Decimal
    bom_id: int
    bom_version: Optional[str] = None
    warehouse_id: int
    raw_material_warehouse_id: int
    planned_start_date: date
    planned_end_date: date
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    status: str
    total_material_cost: Decimal
    total_labor_cost: Decimal
    total_overhead_cost: Decimal
    total_cost: Decimal
    remark: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    details: List[MoDetailResponse] = []
    routings: List[MoRoutingResponse] = []


class MoOrderBrief(BaseModel):
    """生产订单简要信息"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    mo_no: str
    product_sku_id: str
    product_sku_name: str
    planned_qty: Decimal
    status: str
    planned_start_date: date
    created_at: datetime


# ============ 操作 Schema ============

class MoReleaseRequest(BaseModel):
    """下达生产订单请求"""
    pass


class MoStartRequest(BaseModel):
    """开工请求"""
    pass


class MoCompleteRequest(BaseModel):
    """完工请求"""
    actual_end_date: Optional[date] = Field(None, description="实际完工日期")


class MoIssueMaterialRequest(BaseModel):
    """发料请求"""
    items: List[dict] = Field(..., description="发料明细")
    remark: Optional[str] = Field(None, description="备注")


class MoConsumeMaterialRequest(BaseModel):
    """消耗物料请求"""
    items: List[dict] = Field(..., description="消耗明细")
    remark: Optional[str] = Field(None, description="备注")


# ============ 查询 Schema ============

class MoOrderQuery(BaseModel):
    """生产订单查询参数"""
    mo_no: Optional[str] = Field(None, description="生产单号")
    product_sku_id: Optional[str] = Field(None, description="成品SKU ID")
    status: Optional[MoStatus] = Field(None, description="状态")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ============ 事件 Schema ============

class MoStartedEvent(BaseModel):
    """生产订单开工事件"""
    event_type: str = "MoStarted"
    mo_no: str
    product_sku_id: str
    planned_qty: Decimal
    warehouse_id: int
    raw_material_warehouse_id: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MoCompletedEvent(BaseModel):
    """生产订单完工事件"""
    event_type: str = "MoCompleted"
    mo_no: str
    product_sku_id: str
    planned_qty: Decimal
    actual_qty: Decimal
    timestamp: datetime = Field(default_factory=datetime.utcnow)
