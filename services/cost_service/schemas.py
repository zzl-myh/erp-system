"""成本中心 - Pydantic Schema"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============ 枚举类型 ============

class CostType(str, Enum):
    """成本类型"""
    PURCHASE = "PURCHASE"       # 采购成本
    PRODUCTION = "PRODUCTION"   # 生产成本
    SALE = "SALE"               # 销售成本


class CostSheetStatus(str, Enum):
    """成本单状态"""
    DRAFT = "DRAFT"     # 草稿
    POSTED = "POSTED"   # 已过账
    CLOSED = "CLOSED"   # 已关闭


class AllocationMethod(str, Enum):
    """分摊方法"""
    RATIO = "RATIO"         # 比例
    EQUAL = "EQUAL"         # 平均
    WEIGHTED = "WEIGHTED"   # 加权


class AllocationBase(str, Enum):
    """分摊基数"""
    QTY = "QTY"             # 数量
    AMOUNT = "AMOUNT"       # 金额
    WORK_HOURS = "WORK_HOURS"  # 工时


# ============ 成本核算单 Schema ============

class CostSheetBase(BaseModel):
    """成本核算单基础"""
    sku_id: str = Field(..., max_length=50, description="SKU ID")
    sku_name: str = Field(..., max_length=200, description="SKU名称")
    cost_type: CostType = Field(..., description="成本类型")
    quantity: Decimal = Field(..., ge=0, description="核算数量")
    period_start: date = Field(..., description="期间开始")
    period_end: date = Field(..., description="期间结束")
    source_type: str = Field(..., max_length=20, description="来源类型")
    source_no: Optional[str] = Field(None, max_length=50, description="来源单号")


class CostItemBase(BaseModel):
    """成本明细基础"""
    item_code: str = Field(..., max_length=20, description="成本项目编码")
    item_name: str = Field(..., max_length=100, description="成本项目名称")
    amount: Decimal = Field(..., ge=0, description="金额")
    quantity: Optional[Decimal] = Field(None, ge=0, description="数量")
    allocation_base: Optional[AllocationBase] = Field(None, description="分摊基数")
    allocation_value: Optional[Decimal] = Field(None, ge=0, description="分摊值")
    source_detail: Optional[str] = Field(None, description="来源明细")


class CostItemCreate(CostItemBase):
    """创建成本明细"""
    pass


class CostItemResponse(CostItemBase):
    """成本明细响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    sheet_id: int


class CostSheetCreate(CostSheetBase):
    """创建成本核算单"""
    items: List[CostItemCreate] = Field(..., min_length=1, description="成本明细")
    remark: Optional[str] = Field(None, description="备注")


class CostSheetUpdate(BaseModel):
    """更新成本核算单"""
    remark: Optional[str] = Field(None, description="备注")


class CostSheetResponse(CostSheetBase):
    """成本核算单响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    sheet_no: str
    material_cost: Decimal
    labor_cost: Decimal
    overhead_cost: Decimal
    total_cost: Decimal
    unit_cost: Decimal
    status: str
    posted_by: Optional[str] = None
    remark: Optional[str] = None
    created_by: Optional[str] = None
    posted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[CostItemResponse] = []


# ============ 产品标准成本 Schema ============

class ProductCostBase(BaseModel):
    """产品标准成本基础"""
    sku_id: str = Field(..., max_length=50, description="SKU ID")
    sku_name: str = Field(..., max_length=200, description="SKU名称")
    std_material_cost: Decimal = Field(..., ge=0, description="标准原料成本")
    std_labor_cost: Decimal = Field(..., ge=0, description="标准人工成本")
    std_overhead_cost: Decimal = Field(..., ge=0, description="标准制造费用")


class ProductCostCreate(ProductCostBase):
    """创建产品标准成本"""
    version: str = Field(default="V1.0", max_length=20, description="版本号")
    effective_date: date = Field(..., description="生效日期")
    remark: Optional[str] = Field(None, description="备注")


class ProductCostUpdate(BaseModel):
    """更新产品标准成本"""
    std_material_cost: Optional[Decimal] = Field(None, ge=0, description="标准原料成本")
    std_labor_cost: Optional[Decimal] = Field(None, ge=0, description="标准人工成本")
    std_overhead_cost: Optional[Decimal] = Field(None, ge=0, description="标准制造费用")
    version: Optional[str] = Field(None, max_length=20, description="版本号")
    effective_date: Optional[date] = Field(None, description="生效日期")
    remark: Optional[str] = Field(None, description="备注")


class ProductCostResponse(ProductCostBase):
    """产品标准成本响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    std_total_cost: Decimal
    status: str
    version: str
    effective_date: date
    remark: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ 成本分摊规则 Schema ============

class CostAllocationRuleBase(BaseModel):
    """成本分摊规则基础"""
    rule_code: str = Field(..., max_length=50, description="规则编码")
    rule_name: str = Field(..., max_length=200, description="规则名称")
    target_type: str = Field(..., max_length=20, description="分摊目标类型")
    base_type: str = Field(..., max_length=20, description="分摊基数类型")
    allocation_method: AllocationMethod = Field(..., description="分摊方法")


class CostAllocationRuleCreate(CostAllocationRuleBase):
    """创建成本分摊规则"""
    target_condition: Optional[str] = Field(None, description="分摊目标条件")
    base_condition: Optional[str] = Field(None, description="分摊基数条件")
    ratio_formula: Optional[str] = Field(None, description="分摊比例公式")
    remark: Optional[str] = Field(None, description="备注")


class CostAllocationRuleUpdate(BaseModel):
    """更新成本分摊规则"""
    rule_name: Optional[str] = Field(None, max_length=200, description="规则名称")
    target_type: Optional[str] = Field(None, max_length=20, description="分摊目标类型")
    target_condition: Optional[str] = Field(None, description="分摊目标条件")
    base_type: Optional[str] = Field(None, max_length=20, description="分摊基数类型")
    base_condition: Optional[str] = Field(None, description="分摊基数条件")
    allocation_method: Optional[AllocationMethod] = Field(None, description="分摊方法")
    ratio_formula: Optional[str] = Field(None, description="分摊比例公式")
    remark: Optional[str] = Field(None, description="备注")


class CostAllocationRuleResponse(CostAllocationRuleBase):
    """成本分摊规则响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: str
    remark: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ 计算请求 Schema ============

class CalculateCostRequest(BaseModel):
    """成本计算请求"""
    sku_id: str = Field(..., max_length=50, description="SKU ID")
    cost_type: CostType = Field(..., description="成本类型")
    quantity: Decimal = Field(..., gt=0, description="数量")
    period_start: date = Field(..., description="期间开始")
    period_end: date = Field(..., description="期间结束")
    source_type: str = Field(..., max_length=20, description="来源类型")
    source_no: str = Field(..., max_length=50, description="来源单号")


class CalculateCostResponse(BaseModel):
    """成本计算响应"""
    sku_id: str
    cost_type: str
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    details: dict


# ============ 查询 Schema ============

class CostSheetQuery(BaseModel):
    """成本核算单查询参数"""
    sku_id: Optional[str] = Field(None, description="SKU ID")
    cost_type: Optional[CostType] = Field(None, description="成本类型")
    status: Optional[CostSheetStatus] = Field(None, description="状态")
    period_start: Optional[date] = Field(None, description="期间开始")
    period_end: Optional[date] = Field(None, description="期间结束")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ============ 事件 Schema ============

class CostCalculatedEvent(BaseModel):
    """成本计算完成事件"""
    event_type: str = "CostCalculated"
    sheet_no: str
    sku_id: str
    cost_type: str
    unit_cost: Decimal
    total_cost: Decimal
    timestamp: datetime = Field(default_factory=datetime.utcnow)
