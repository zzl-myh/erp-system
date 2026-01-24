"""成本中心 - SQLAlchemy 模型"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger, String, Integer, DECIMAL, DateTime, Text, Date,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp_common.database import Base


class CostSheet(Base):
    """成本核算单表"""
    __tablename__ = "cost_sheet"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sheet_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="成本单号")
    
    # 核算对象
    sku_id: Mapped[str] = mapped_column(String(50), nullable=False, comment="SKU ID")
    sku_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="SKU名称")
    
    # 成本类型
    cost_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="成本类型: PURCHASE/PRODUCTION/SALE")
    
    # 成本构成
    material_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="原料成本")
    labor_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="人工成本")
    overhead_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="制造费用")
    total_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="总成本")
    
    # 数量
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="核算数量")
    unit_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="单位成本")
    
    # 核算期间
    period_start: Mapped[datetime] = mapped_column(Date, comment="期间开始")
    period_end: Mapped[datetime] = mapped_column(Date, comment="期间结束")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", comment="状态: DRAFT/POSTED/CLOSED")
    
    # 来源单据
    source_type: Mapped[str] = mapped_column(String(20), comment="来源类型")
    source_no: Mapped[Optional[str]] = mapped_column(String(50), comment="来源单号")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    created_by: Mapped[Optional[str]] = mapped_column(String(50), comment="创建人")
    posted_by: Mapped[Optional[str]] = mapped_column(String(50), comment="过账人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="过账时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_sheet_no", "sheet_no"),
        Index("idx_sheet_sku", "sku_id"),
        Index("idx_sheet_type", "cost_type"),
        Index("idx_sheet_period", "period_start", "period_end"),
        Index("idx_sheet_status", "status"),
    )


class CostItem(Base):
    """成本明细表"""
    __tablename__ = "cost_item"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sheet_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cost_sheet.id"), nullable=False)
    
    # 成本项目
    item_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="成本项目编码")
    item_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="成本项目名称")
    
    # 金额
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False, comment="金额")
    
    # 数量
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="数量")
    
    # 分摊基数
    allocation_base: Mapped[Optional[str]] = mapped_column(String(20), comment="分摊基数: QTY/AMOUNT/WORK_HOURS")
    allocation_value: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="分摊值")
    
    # 来源
    source_detail: Mapped[Optional[str]] = mapped_column(Text, comment="来源明细")
    
    # 关联
    sheet: Mapped["CostSheet"] = relationship(back_populates="items")
    
    __table_args__ = (
        Index("idx_item_sheet", "sheet_id"),
        Index("idx_item_code", "item_code"),
    )


class ProductCost(Base):
    """产品标准成本表"""
    __tablename__ = "product_cost"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sku_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="SKU ID")
    sku_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="SKU名称")
    
    # 标准成本构成
    std_material_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="标准原料成本")
    std_labor_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="标准人工成本")
    std_overhead_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="标准制造费用")
    std_total_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), default=0, comment="标准总成本")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", comment="状态: ACTIVE/INACTIVE")
    
    # 版本
    version: Mapped[str] = mapped_column(String(20), default="V1.0", comment="版本号")
    effective_date: Mapped[datetime] = mapped_column(Date, comment="生效日期")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    created_by: Mapped[Optional[str]] = mapped_column(String(50), comment="创建人")
    updated_by: Mapped[Optional[str]] = mapped_column(String(50), comment="更新人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_pc_sku", "sku_id"),
        Index("idx_pc_status", "status"),
    )


class CostAllocationRule(Base):
    """成本分摊规则表"""
    __tablename__ = "cost_allocation_rule"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="规则编码")
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="规则名称")
    
    # 分摊对象
    target_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="分摊目标类型")
    target_condition: Mapped[Optional[str]] = mapped_column(Text, comment="分摊目标条件")
    
    # 分摊基数
    base_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="分摊基数类型")
    base_condition: Mapped[Optional[str]] = mapped_column(Text, comment="分摊基数条件")
    
    # 分摊方法
    allocation_method: Mapped[str] = mapped_column(String(20), nullable=False, comment="分摊方法: RATIO/EQUAL/WEIGHTED")
    ratio_formula: Mapped[Optional[str]] = mapped_column(Text, comment="分摊比例公式")
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", comment="状态")
    
    # 备注
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注")
    
    # 操作人
    created_by: Mapped[Optional[str]] = mapped_column(String(50), comment="创建人")
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_car_code", "rule_code"),
        Index("idx_car_target", "target_type"),
        Index("idx_car_status", "status"),
    )
