"""
商品中心 - SQLAlchemy 数据模型
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from erp_common.database import Base


class Item(Base):
    """商品主表"""
    
    __tablename__ = "item"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sku_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="全局唯一SKU编码")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="商品名称")
    category_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("item_category.id"), comment="分类ID")
    unit: Mapped[Optional[str]] = mapped_column(String(20), comment="计量单位")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态: 1启用 0停用")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="商品描述")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    
    # 关系
    skus: Mapped[List["ItemSku"]] = relationship("ItemSku", back_populates="item", lazy="selectin")
    barcodes: Mapped[List["ItemBarcode"]] = relationship("ItemBarcode", back_populates="item", lazy="selectin")
    category: Mapped[Optional["ItemCategory"]] = relationship("ItemCategory", back_populates="items", lazy="selectin")


class ItemSku(Base):
    """商品SKU表"""
    
    __tablename__ = "item_sku"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("item.id"), nullable=False)
    sku_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    spec_info: Mapped[Optional[dict]] = mapped_column(JSON, comment="规格信息")
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="销售价")
    cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment="成本价")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关系
    item: Mapped["Item"] = relationship("Item", back_populates="skus")


class ItemBarcode(Base):
    """商品条码表"""
    
    __tablename__ = "item_barcode"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("item.id"), nullable=False)
    sku_id: Mapped[str] = mapped_column(String(32), nullable=False)
    barcode: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_primary: Mapped[int] = mapped_column(Integer, default=0, comment="是否主条码")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关系
    item: Mapped["Item"] = relationship("Item", back_populates="barcodes")


class ItemCategory(Base):
    """商品分类表"""
    
    __tablename__ = "item_category"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[int] = mapped_column(BigInteger, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关系
    items: Mapped[List["Item"]] = relationship("Item", back_populates="category")
