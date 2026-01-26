"""报工中心 - SQLAlchemy 模型"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger, String, Integer, DECIMAL, DateTime, Text, Date,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp_common.database import Base


class ReportJob(Base):
    """报工记录表"""
    __tablename__ = "report_job"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="报工单号")
    
    # 生产订单信息
    mo_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="生产订单ID")
    mo_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="生产订单号")
    
    # 产品信息
    product_sku_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="成品SKU ID")
    product_sku_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="成品SKU名称")
    
    # 报工数量
    reported_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="报工数量")
    qualified_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="合格数量")
    unqualified_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="不合格数量")
    
    # 工时
    work_hours: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), comment="工时")
    
    # 工人信息
    worker_id: Mapped[Optional[int]] = mapped_column(BigInteger, comment="工人ID")
    worker_name: Mapped[Optional[str]] = mapped_column(String(50), comment="工人姓名")
    
    # 设备信息
    equipment_id: Mapped[Optional[int]] = mapped_column(BigInteger, comment="设备ID")
    equipment_name: Mapped[Optional[str]] = mapped_column(String(100), comment="设备名称")
    
    # 班组信息
    team_id: Mapped[Optional[int]] = mapped_column(BigInteger, comment="班组ID")
    team_name: Mapped[Optional[str]] = mapped_column(String(50), comment="班组名称")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="REPORTED", comment="状态: REPORTED/CONFIRMED/REJECTED")
    
    # 时间
    report_date: Mapped[datetime] = mapped_column(Date, default=date.today, comment="报工日期")
    report_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="报工时间")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    reported_by: Mapped[Optional[str]] = mapped_column(String(50), comment="报工人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_report_no", "report_no"),
        Index("idx_report_mo", "mo_id"),
        Index("idx_report_product", "product_sku_id"),
        Index("idx_report_worker", "worker_id"),
        Index("idx_report_date", "report_date"),
    )


class ReportLoss(Base):
    """报损记录表"""
    __tablename__ = "report_loss"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    loss_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="报损单号")
    
    # 生产订单信息
    mo_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="生产订单ID")
    mo_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="生产订单号")
    
    # 损耗物料信息
    material_sku_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="物料SKU ID")
    material_sku_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="物料SKU名称")
    
    # 损耗数量
    loss_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="损耗数量")
    
    # 损耗类型
    loss_type: Mapped[str] = mapped_column(String(20), comment="损耗类型: BREAKAGE/WASTE/SCRAP/OTHER")
    
    # 损耗原因
    loss_reason: Mapped[Optional[str]] = mapped_column(String(200), comment="损耗原因")
    
    # 时间
    loss_date: Mapped[datetime] = mapped_column(Date, default=date.today, comment="报损日期")
    loss_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="报损时间")
    
    # 操作人
    reported_by: Mapped[Optional[str]] = mapped_column(String(50), comment="报损人")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_loss_no", "loss_no"),
        Index("idx_loss_mo", "mo_id"),
        Index("idx_loss_material", "material_sku_id"),
        Index("idx_loss_date", "loss_date"),
    )


class MoWorkHour(Base):
    """生产工时记录表"""
    __tablename__ = "mo_work_hour"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mo_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="生产订单ID")
    mo_no: Mapped[str] = mapped_column(String(50), nullable=False, comment="生产订单号")
    
    # 工人信息
    worker_id: Mapped[Optional[int]] = mapped_column(BigInteger, comment="工人ID")
    worker_name: Mapped[Optional[str]] = mapped_column(String(50), comment="工人姓名")
    
    # 工时信息
    work_date: Mapped[datetime] = mapped_column(Date, default=date.today, comment="工作日期")
    work_hours: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False, comment="工时")
    
    # 工作内容
    work_content: Mapped[Optional[str]] = mapped_column(String(200), comment="工作内容")
    
    # 操作人
    recorded_by: Mapped[Optional[str]] = mapped_column(String(50), comment="记录人")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_mwh_mo", "mo_id"),
        Index("idx_mwh_worker", "worker_id"),
        Index("idx_mwh_date", "work_date"),
    )
