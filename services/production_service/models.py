"""生产中心 - SQLAlchemy 模型"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger, String, Integer, DECIMAL, DateTime, Text, Date,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp_common.database import Base


class BomTemplate(Base):
    """BOM模板表"""
    __tablename__ = "bom_template"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="BOM编码")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="BOM名称")
    
    # 物料信息
    product_sku_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="成品SKU ID")
    product_sku_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="成品SKU名称")
    
    # 版本
    version: Mapped[str] = mapped_column(String(20), default="V1.0", comment="版本号")
    revision: Mapped[int] = mapped_column(Integer, default=1, comment="修订次数")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", comment="状态: ACTIVE/INACTIVE")
    
    # 有效期
    valid_from: Mapped[datetime] = mapped_column(Date, comment="生效日期")
    valid_to: Mapped[Optional[datetime]] = mapped_column(Date, comment="失效日期")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    items: Mapped[List["BomTemplateItem"]] = relationship(back_populates="template", lazy="selectin", cascade="all, delete-orphan")


class BomTemplateItem(Base):
    """BOM模板明细表"""
    __tablename__ = "bom_template_item"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bom_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bom_template.id"), nullable=False)
    
    # 物料信息
    material_sku_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="物料SKU ID")
    material_sku_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="物料SKU名称")
    
    # 数量
    qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="需求数量")
    unit: Mapped[Optional[str]] = mapped_column(String(20), comment="单位")
    
    # 行号
    line_no: Mapped[int] = mapped_column(Integer, default=1, comment="行号")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(String(500), comment="备注")
    
    # 关联
    template: Mapped["BomTemplate"] = relationship(back_populates="items")
    
    __table_args__ = (
        Index("idx_bti_bom", "bom_id"),
        Index("idx_bti_material", "material_sku_id"),
    )


class MoOrder(Base):
    """生产订单主表"""
    __tablename__ = "mo_order"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mo_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="生产单号")
    
    # 产品信息
    product_sku_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="成品SKU ID")
    product_sku_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="成品SKU名称")
    planned_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="计划生产数量")
    
    # BOM信息
    bom_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="BOM模板ID")
    bom_version: Mapped[str] = mapped_column(String(20), comment="BOM版本")
    
    # 仓库信息
    warehouse_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="生产仓库ID")
    raw_material_warehouse_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="原料仓库ID")
    
    # 日期
    planned_start_date: Mapped[datetime] = mapped_column(Date, comment="计划开工日期")
    planned_end_date: Mapped[datetime] = mapped_column(Date, comment="计划完工日期")
    actual_start_date: Mapped[Optional[datetime]] = mapped_column(Date, comment="实际开工日期")
    actual_end_date: Mapped[Optional[datetime]] = mapped_column(Date, comment="实际完工日期")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", comment="状态: DRAFT/RELEASED/STARTED/PAUSED/COMPLETED/CANCELLED")
    
    # 金额
    total_material_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="总原料成本")
    total_labor_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="总人工成本")
    total_overhead_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="总制造费用")
    total_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, comment="总成本")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 创建人
    created_by: Mapped[Optional[str]] = mapped_column(String(50), comment="创建人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    details: Mapped[List["MoDetail"]] = relationship(back_populates="order", lazy="selectin", cascade="all, delete-orphan")
    routings: Mapped[List["MoRouting"]] = relationship(back_populates="order", lazy="selectin", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_mo_no", "mo_no"),
        Index("idx_mo_product", "product_sku_id"),
        Index("idx_mo_status", "status"),
        Index("idx_mo_date", "planned_start_date"),
    )


class MoDetail(Base):
    """生产订单明细表（物料需求）"""
    __tablename__ = "mo_detail"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mo_order.id"), nullable=False)
    
    # 物料信息
    material_sku_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="物料SKU ID")
    material_sku_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="物料SKU名称")
    
    # 需求信息
    required_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="需求数量")
    issued_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="已发料数量")
    consumed_qty: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="已消耗数量")
    
    # 单位
    unit: Mapped[Optional[str]] = mapped_column(String(20), comment="单位")
    
    # 行号
    line_no: Mapped[int] = mapped_column(Integer, default=1, comment="行号")
    
    # 关联
    order: Mapped["MoOrder"] = relationship(back_populates="details")
    
    __table_args__ = (
        Index("idx_mod_mo", "mo_id"),
        Index("idx_mod_material", "material_sku_id"),
    )


class MoRouting(Base):
    """生产工序表"""
    __tablename__ = "mo_routing"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mo_order.id"), nullable=False)
    
    # 工序信息
    operation_no: Mapped[str] = mapped_column(String(20), nullable=False, comment="工序编号")
    operation_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="工序名称")
    
    # 工序描述
    description: Mapped[Optional[str]] = mapped_column(String(500), comment="工序描述")
    
    # 工时
    planned_hours: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), comment="计划工时")
    actual_hours: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), comment="实际工时")
    
    # 优先级
    priority: Mapped[int] = mapped_column(Integer, default=1, comment="优先级")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="PENDING", comment="状态: PENDING/IN_PROGRESS/COMPLETED")
    
    # 时间
    planned_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="计划开始时间")
    planned_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="计划结束时间")
    actual_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="实际开始时间")
    actual_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="实际结束时间")
    
    # 关联
    order: Mapped["MoOrder"] = relationship(back_populates="routings")
    
    __table_args__ = (
        Index("idx_mr_mo", "mo_id"),
        Index("idx_mr_operation", "operation_no"),
        UniqueConstraint("mo_id", "operation_no", name="uk_mo_operation"),
    )
