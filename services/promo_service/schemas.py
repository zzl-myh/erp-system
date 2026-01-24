"""促销中心 - Pydantic Schema"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============ 枚举类型 ============

class PromoType(str, Enum):
    """促销类型"""
    FULL_REDUCTION = "FULL_REDUCTION"  # 满减
    DISCOUNT = "DISCOUNT"              # 折扣
    BUY_GIFT = "BUY_GIFT"              # 买赠
    BUY_MORE = "BUY_MORE"              # 买多
    BUNDLE = "BUNDLE"                  # 组合


class ScopeType(str, Enum):
    """适用范围类型"""
    ALL = "ALL"           # 全部
    CATEGORY = "CATEGORY" # 分类
    SKU = "SKU"           # SKU
    BRAND = "BRAND"       # 品牌


class ConditionType(str, Enum):
    """条件类型"""
    AMOUNT = "AMOUNT"  # 金额
    QTY = "QTY"        # 数量


class BenefitType(str, Enum):
    """优惠类型"""
    REDUCE = "REDUCE"    # 减金额
    PERCENT = "PERCENT"  # 百分比
    POINTS = "POINTS"    # 积分
    GIFT = "GIFT"        # 赠品


class PromoStatus(str, Enum):
    """促销状态"""
    DRAFT = "DRAFT"       # 草稿
    ACTIVE = "ACTIVE"     # 激活
    INACTIVE = "INACTIVE" # 停用
    EXPIRED = "EXPIRED"   # 过期


class CombinationType(str, Enum):
    """组合类型"""
    AND = "AND"       # 且
    OR = "OR"         # 或
    SEQUENCE = "SEQUENCE"  # 顺序


class OperatorType(str, Enum):
    """操作符类型"""
    EQ = "EQ"    # 等于
    GT = "GT"    # 大于
    LT = "LT"    # 小于
    GTE = "GTE"  # 大于等于
    LTE = "LTE"  # 小于等于
    IN = "IN"    # 包含


class BenefitOperatorType(str, Enum):
    """优惠操作符类型"""
    SET = "SET"  # 设置
    ADD = "ADD"  # 增加
    SUB = "SUB"  # 减少
    MUL = "MUL"  # 乘以


# ============ 促销活动 Schema ============

class PromoRuleBase(BaseModel):
    """促销规则基础"""
    name: str = Field(..., max_length=100, description="规则名称")
    condition_field: str = Field(..., max_length=50, description="条件字段")
    condition_operator: OperatorType = Field(..., description="条件操作符")
    condition_value: str = Field(..., description="条件值")
    benefit_field: str = Field(..., max_length=50, description="优惠字段")
    benefit_operator: BenefitOperatorType = Field(..., description="优惠操作符")
    benefit_value: str = Field(..., description="优惠值")
    priority: int = Field(default=1, description="优先级")
    status: str = Field(default="ACTIVE", description="状态")


class PromoRuleCreate(PromoRuleBase):
    """创建促销规则"""
    pass


class PromoRuleResponse(PromoRuleBase):
    """促销规则响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    promo_id: int


class PromoBase(BaseModel):
    """促销活动基础"""
    code: str = Field(..., max_length=50, description="促销编码")
    name: str = Field(..., max_length=200, description="促销名称")
    promo_type: PromoType = Field(..., description="促销类型")
    scope_type: ScopeType = Field(default=ScopeType.ALL, description="适用范围类型")
    condition_type: ConditionType = Field(default=ConditionType.AMOUNT, description="条件类型")
    condition_value: Decimal = Field(..., ge=0, description="条件值")
    benefit_type: BenefitType = Field(..., description="优惠类型")
    benefit_value: Decimal = Field(..., description="优惠值")
    valid_from: date = Field(..., description="有效开始日期")
    valid_to: date = Field(..., description="有效结束日期")
    priority: int = Field(default=1, description="优先级")


class PromoCreate(PromoBase):
    """创建促销活动"""
    scope_value: Optional[str] = Field(None, description="适用范围值(JSON格式)")
    max_discount: Decimal = Field(default=0, ge=0, description="最大优惠金额")
    min_qty: Decimal = Field(default=1, ge=0, description="最小购买数量")
    max_qty: Decimal = Field(default=0, ge=0, description="最大购买数量(0为无限制)")
    usage_limit: int = Field(default=0, ge=0, description="使用次数限制(0为无限制)")
    rules: List[PromoRuleCreate] = Field(default=[], description="促销规则")
    remark: Optional[str] = Field(None, description="备注")


class PromoUpdate(BaseModel):
    """更新促销活动"""
    name: Optional[str] = Field(None, max_length=200, description="促销名称")
    promo_type: Optional[PromoType] = Field(None, description="促销类型")
    scope_type: Optional[ScopeType] = Field(None, description="适用范围类型")
    scope_value: Optional[str] = Field(None, description="适用范围值(JSON格式)")
    condition_type: Optional[ConditionType] = Field(None, description="条件类型")
    condition_value: Optional[Decimal] = Field(None, ge=0, description="条件值")
    benefit_type: Optional[BenefitType] = Field(None, description="优惠类型")
    benefit_value: Optional[Decimal] = Field(None, description="优惠值")
    max_discount: Optional[Decimal] = Field(None, ge=0, description="最大优惠金额")
    min_qty: Optional[Decimal] = Field(None, ge=0, description="最小购买数量")
    max_qty: Optional[Decimal] = Field(None, ge=0, description="最大购买数量(0为无限制)")
    usage_limit: Optional[int] = Field(None, ge=0, description="使用次数限制(0为无限制)")
    valid_from: Optional[date] = Field(None, description="有效开始日期")
    valid_to: Optional[date] = Field(None, description="有效结束日期")
    priority: Optional[int] = Field(None, description="优先级")
    status: Optional[PromoStatus] = Field(None, description="状态")
    remark: Optional[str] = Field(None, description="备注")


class PromoResponse(PromoBase):
    """促销活动响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    scope_value: Optional[str] = None
    max_discount: Decimal
    min_qty: Decimal
    max_qty: Decimal
    usage_limit: int
    status: str
    priority: int
    remark: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    rules: List[PromoRuleResponse] = []


# ============ 促销记录 Schema ============

class PromoRecordBase(BaseModel):
    """促销记录基础"""
    promo_id: int = Field(..., description="促销ID")
    promo_code: str = Field(..., max_length=50, description="促销编码")
    promo_name: str = Field(..., max_length=200, description="促销名称")
    order_no: str = Field(..., max_length=50, description="订单号")
    sku_id: Optional[str] = Field(None, max_length=50, description="SKU ID")
    sku_name: Optional[str] = Field(None, max_length=200, description="SKU名称")
    benefit_type: BenefitType = Field(..., description="优惠类型")
    benefit_value: Decimal = Field(..., description="优惠金额/折扣")
    original_price: Decimal = Field(..., description="原始价格")
    final_price: Decimal = Field(..., description="最终价格")
    qty: Decimal = Field(default=1, gt=0, description="数量")


class PromoRecordCreate(PromoRecordBase):
    """创建促销记录"""
    remark: Optional[str] = Field(None, description="备注")


class PromoRecordResponse(PromoRecordBase):
    """促销记录响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    promo_no: str
    total_discount: Decimal
    applied_by: Optional[str] = None
    remark: Optional[str] = None
    applied_at: datetime


# ============ 促销组合 Schema ============

class PromoCombinationBase(BaseModel):
    """促销组合基础"""
    name: str = Field(..., max_length=100, description="组合名称")
    combination_type: CombinationType = Field(default=CombinationType.AND, description="组合类型")
    promo_ids: List[int] = Field(..., min_items=1, description="促销ID列表")
    priority: int = Field(default=1, description="优先级")


class PromoCombinationCreate(PromoCombinationBase):
    """创建促销组合"""
    remark: Optional[str] = Field(None, description="备注")


class PromoCombinationUpdate(BaseModel):
    """更新促销组合"""
    name: Optional[str] = Field(None, max_length=100, description="组合名称")
    combination_type: Optional[CombinationType] = Field(None, description="组合类型")
    promo_ids: Optional[List[int]] = Field(None, min_items=1, description="促销ID列表")
    priority: Optional[int] = Field(None, description="优先级")
    status: Optional[str] = Field(None, description="状态")
    remark: Optional[str] = Field(None, description="备注")


class PromoCombinationResponse(PromoCombinationBase):
    """促销组合响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: str
    remark: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ 促销计算 Schema ============

class CalcPromoRequest(BaseModel):
    """促销计算请求"""
    order_no: str = Field(..., max_length=50, description="订单号")
    items: List[Dict[str, Any]] = Field(..., description="商品明细")
    customer_id: Optional[int] = Field(None, description="客户ID")


class CalcPromoResponse(BaseModel):
    """促销计算响应"""
    order_no: str
    original_total: Decimal
    final_total: Decimal
    total_discount: Decimal
    applied_promos: List[Dict[str, Any]]
    item_details: List[Dict[str, Any]]


class ApplyPromoRequest(BaseModel):
    """应用促销请求"""
    order_no: str = Field(..., max_length=50, description="订单号")
    promo_id: int = Field(..., description="促销ID")
    items: List[Dict[str, Any]] = Field(..., description="商品明细")


# ============ 查询 Schema ============

class PromoQuery(BaseModel):
    """促销查询参数"""
    code: Optional[str] = Field(None, description="促销编码")
    promo_type: Optional[PromoType] = Field(None, description="促销类型")
    status: Optional[PromoStatus] = Field(None, description="状态")
    valid_from: Optional[date] = Field(None, description="有效开始日期")
    valid_to: Optional[date] = Field(None, description="有效结束日期")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ============ 事件 Schema ============

class PromoAppliedEvent(BaseModel):
    """促销应用事件"""
    event_type: str = "PromoApplied"
    promo_id: int
    promo_code: str
    order_no: str
    total_discount: Decimal
    applied_by: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
