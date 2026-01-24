"""报工中心 - Pydantic Schema"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============ 枚举类型 ============

class ReportJobStatus(str, Enum):
    """报工状态"""
    REPORTED = "REPORTED"     # 已报工
    CONFIRMED = "CONFIRMED"   # 已确认
    REJECTED = "REJECTED"     # 已拒绝


class LossType(str, Enum):
    """损耗类型"""
    BREAKAGE = "BREAKAGE"   # 破损
    WASTE = "WASTE"         # 浪费
    SCRAP = "SCRAP"         # 报废
    OTHER = "OTHER"         # 其他


# ============ 报工 Schema ============

class ReportJobBase(BaseModel):
    """报工基础"""
    mo_id: int = Field(..., description="生产订单ID")
    mo_no: str = Field(..., max_length=50, description="生产订单号")
    product_sku_id: str = Field(..., max_length=50, description="成品SKU ID")
    product_sku_name: str = Field(..., max_length=200, description="成品SKU名称")
    reported_qty: Decimal = Field(..., gt=0, description="报工数量")
    qualified_qty: Decimal = Field(default=0, ge=0, description="合格数量")
    unqualified_qty: Decimal = Field(default=0, ge=0, description="不合格数量")
    work_hours: Optional[Decimal] = Field(None, ge=0, description="工时")
    worker_id: Optional[int] = Field(None, description="工人ID")
    worker_name: Optional[str] = Field(None, max_length=50, description="工人姓名")
    equipment_id: Optional[int] = Field(None, description="设备ID")
    equipment_name: Optional[str] = Field(None, max_length=100, description="设备名称")
    team_id: Optional[int] = Field(None, description="班组ID")
    team_name: Optional[str] = Field(None, max_length=50, description="班组名称")


class ReportJobCreate(ReportJobBase):
    """创建报工"""
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class ReportJobUpdate(BaseModel):
    """更新报工"""
    status: Optional[ReportJobStatus] = Field(None, description="状态")
    qualified_qty: Optional[Decimal] = Field(None, ge=0, description="合格数量")
    unqualified_qty: Optional[Decimal] = Field(None, ge=0, description="不合格数量")
    work_hours: Optional[Decimal] = Field(None, ge=0, description="工时")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class ReportJobResponse(ReportJobBase):
    """报工响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    report_no: str
    status: str
    report_date: date
    report_time: datetime
    remark: Optional[str] = None
    reported_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ 报损 Schema ============

class ReportLossBase(BaseModel):
    """报损基础"""
    mo_id: int = Field(..., description="生产订单ID")
    mo_no: str = Field(..., max_length=50, description="生产订单号")
    material_sku_id: str = Field(..., max_length=50, description="物料SKU ID")
    material_sku_name: str = Field(..., max_length=200, description="物料SKU名称")
    loss_qty: Decimal = Field(..., gt=0, description="损耗数量")
    loss_type: LossType = Field(..., description="损耗类型")
    loss_reason: Optional[str] = Field(None, max_length=200, description="损耗原因")


class ReportLossCreate(ReportLossBase):
    """创建报损"""
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class ReportLossResponse(ReportLossBase):
    """报损响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    loss_no: str
    loss_date: date
    loss_time: datetime
    reported_by: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ 工时 Schema ============

class MoWorkHourBase(BaseModel):
    """工时基础"""
    mo_id: int = Field(..., description="生产订单ID")
    mo_no: str = Field(..., max_length=50, description="生产订单号")
    worker_id: Optional[int] = Field(None, description="工人ID")
    worker_name: Optional[str] = Field(None, max_length=50, description="工人姓名")
    work_date: date = Field(..., description="工作日期")
    work_hours: Decimal = Field(..., gt=0, description="工时")


class MoWorkHourCreate(MoWorkHourBase):
    """创建工时"""
    work_content: Optional[str] = Field(None, max_length=200, description="工作内容")
    remark: Optional[str] = Field(None, max_length=500, description="备注")


class MoWorkHourResponse(MoWorkHourBase):
    """工时响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    recorded_by: Optional[str] = None
    work_content: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime


# ============ 查询 Schema ============

class ReportJobQuery(BaseModel):
    """报工查询参数"""
    mo_id: Optional[int] = Field(None, description="生产订单ID")
    mo_no: Optional[str] = Field(None, description="生产订单号")
    product_sku_id: Optional[str] = Field(None, description="成品SKU ID")
    worker_id: Optional[int] = Field(None, description="工人ID")
    status: Optional[ReportJobStatus] = Field(None, description="状态")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class ReportLossQuery(BaseModel):
    """报损查询参数"""
    mo_id: Optional[int] = Field(None, description="生产订单ID")
    mo_no: Optional[str] = Field(None, description="生产订单号")
    material_sku_id: Optional[str] = Field(None, description="物料SKU ID")
    loss_type: Optional[LossType] = Field(None, description="损耗类型")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


# ============ 事件 Schema ============

class JobReportedEvent(BaseModel):
    """报工事件"""
    event_type: str = "JobReported"
    report_no: str
    mo_no: str
    product_sku_id: str
    reported_qty: Decimal
    qualified_qty: Decimal
    unqualified_qty: Decimal
    work_hours: Optional[Decimal] = None
    worker_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MoCompletedEvent(BaseModel):
    """生产订单完工事件（用于通知生产完工）"""
    event_type: str = "MoCompleted"
    mo_no: str
    product_sku_id: str
    planned_qty: Decimal
    actual_qty: Decimal
    timestamp: datetime = Field(default_factory=datetime.utcnow)
