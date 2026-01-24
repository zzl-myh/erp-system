"""采购中心 - Pydantic Schema"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============ 枚举类型 ============

class PoStatus(str, Enum):
    """采购订单状态"""
    DRAFT = "DRAFT"           # 草稿
    PENDING = "PENDING"       # 待审批
    APPROVED = "APPROVED"     # 已审批
    REJECTED = "REJECTED"     # 已拒绝
    RECEIVING = "RECEIVING"   # 收货中
    COMPLETED = "COMPLETED"   # 已完成
    CANCELLED = "CANCELLED"   # 已取消


class SupplierStatus(str, Enum):
    """供应商状态"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


# ============ 供应商 Schema ============

class SupplierBase(BaseModel):
    """供应商基础"""
    code: str = Field(..., max_length=50, description="供应商编码")
    name: str = Field(..., max_length=200, description="供应商名称")
    short_name: Optional[str] = Field(None, max_length=50, description="简称")
    contact_person: Optional[str] = Field(None, max_length=50, description="联系人")
    contact_phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    contact_email: Optional[str] = Field(None, max_length=100, description="邮箱")
    address: Optional[str] = Field(None, max_length=500, description="地址")


class SupplierCreate(SupplierBase):
    """创建供应商"""
    bank_name: Optional[str] = Field(None, max_length=100, description="开户银行")
    bank_account: Optional[str] = Field(None, max_length=50, description="银行账号")
    tax_no: Optional[str] = Field(None, max_length=50, description="税号")
    remark: Optional[str] = Field(None, description="备注")


class SupplierUpdate(BaseModel):
    """更新供应商"""
    name: Optional[str] = Field(None, max_length=200)
    short_name: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=50)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    bank_name: Optional[str] = Field(None, max_length=100)
    bank_account: Optional[str] = Field(None, max_length=50)
    tax_no: Optional[str] = Field(None, max_length=50)
    status: Optional[SupplierStatus] = None
    remark: Optional[str] = None


class SupplierResponse(SupplierBase):
    """供应商响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    tax_no: Optional[str] = None
    status: str
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ 采购订单明细 Schema ============

class PoDetailBase(BaseModel):
    """采购明细基础"""
    sku_id: str = Field(..., max_length=50, description="SKU ID")
    sku_name: str = Field(..., max_length=200, description="SKU 名称")
    qty: Decimal = Field(..., gt=0, description="采购数量")
    unit_price: Decimal = Field(..., ge=0, description="单价")
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, description="税率 %")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class PoDetailCreate(PoDetailBase):
    """创建采购明细"""
    pass


class PoDetailResponse(PoDetailBase):
    """采购明细响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    po_id: int
    amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    received_qty: Decimal
    line_no: int


# ============ 采购订单 Schema ============

class PoOrderCreate(BaseModel):
    """创建采购订单"""
    supplier_id: int = Field(..., description="供应商ID")
    warehouse_id: int = Field(..., description="入库仓库ID")
    expected_date: Optional[date] = Field(None, description="预计到货日期")
    remark: Optional[str] = Field(None, description="备注")
    details: List[PoDetailCreate] = Field(..., min_length=1, description="采购明细")


class PoOrderUpdate(BaseModel):
    """更新采购订单"""
    supplier_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    expected_date: Optional[date] = None
    remark: Optional[str] = None


class PoOrderResponse(BaseModel):
    """采购订单响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    po_no: str
    supplier_id: int
    warehouse_id: int
    total_qty: Decimal
    total_amount: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    payable_amount: Decimal
    status: str
    order_date: date
    expected_date: Optional[date] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    remark: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    details: List[PoDetailResponse] = []


class PoOrderBrief(BaseModel):
    """采购订单简要信息"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    po_no: str
    supplier_id: int
    total_qty: Decimal
    payable_amount: Decimal
    status: str
    order_date: date
    created_at: datetime


# ============ 审批相关 Schema ============

class PoApproveRequest(BaseModel):
    """审批请求"""
    approved: bool = Field(..., description="是否通过")
    reject_reason: Optional[str] = Field(None, max_length=500, description="拒绝原因")


# ============ 收货相关 Schema ============

class ReceiveDetailCreate(BaseModel):
    """收货明细"""
    po_detail_id: int = Field(..., description="采购明细ID")
    sku_id: str = Field(..., max_length=50, description="SKU ID")
    qty: Decimal = Field(..., gt=0, description="收货数量")
    batch_no: Optional[str] = Field(None, max_length=50, description="批次号")
    production_date: Optional[date] = Field(None, description="生产日期")
    expiry_date: Optional[date] = Field(None, description="过期日期")


class PoReceiveRequest(BaseModel):
    """收货请求"""
    po_id: int = Field(..., description="采购订单ID")
    details: List[ReceiveDetailCreate] = Field(..., min_length=1, description="收货明细")
    remark: Optional[str] = Field(None, description="备注")


class ReceiveDetailResponse(BaseModel):
    """收货明细响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    receive_id: int
    po_detail_id: int
    sku_id: str
    qty: Decimal
    unit_cost: Decimal
    batch_no: Optional[str] = None
    production_date: Optional[date] = None
    expiry_date: Optional[date] = None


class PoReceiveResponse(BaseModel):
    """收货响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    receive_no: str
    po_id: int
    receive_date: date
    receiver: Optional[str] = None
    status: str
    remark: Optional[str] = None
    created_at: datetime
    details: List[ReceiveDetailResponse] = []


# ============ 查询 Schema ============

class PoOrderQuery(BaseModel):
    """采购订单查询参数"""
    po_no: Optional[str] = Field(None, description="采购单号")
    supplier_id: Optional[int] = Field(None, description="供应商ID")
    status: Optional[PoStatus] = Field(None, description="状态")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ============ 事件 Schema ============

class PoApprovedEvent(BaseModel):
    """采购订单审批通过事件"""
    event_type: str = "PoApproved"
    po_no: str
    supplier_id: int
    warehouse_id: int
    total_amount: Decimal
    approved_by: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PoInStockEvent(BaseModel):
    """采购入库事件"""
    event_type: str = "PoInStock"
    po_no: str
    receive_no: str
    warehouse_id: int
    items: List[dict]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
