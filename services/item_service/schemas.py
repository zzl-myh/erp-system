"""
商品中心 - Pydantic Schema
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from erp_common.schemas.base import PageQuery, TimestampMixin


# ========== SKU Schema ==========

class SkuSpec(BaseModel):
    """规格信息"""
    name: str
    value: str


class SkuCreate(BaseModel):
    """创建 SKU 请求"""
    spec_info: Optional[dict] = None
    price: Optional[Decimal] = Field(None, ge=0)
    cost: Optional[Decimal] = Field(None, ge=0)


class SkuResponse(BaseModel):
    """SKU 响应"""
    id: int
    sku_id: str
    spec_info: Optional[dict] = None
    price: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    
    class Config:
        from_attributes = True


# ========== Barcode Schema ==========

class BarcodeCreate(BaseModel):
    """创建条码请求"""
    barcode: str = Field(..., min_length=1, max_length=50)
    is_primary: bool = False


class BarcodeResponse(BaseModel):
    """条码响应"""
    id: int
    sku_id: str
    barcode: str
    is_primary: int
    
    class Config:
        from_attributes = True


# ========== Category Schema ==========

class CategoryCreate(BaseModel):
    """创建分类请求"""
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: int = 0
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    """更新分类请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class CategoryResponse(BaseModel):
    """分类响应"""
    id: int
    name: str
    parent_id: int
    level: int
    sort_order: int
    
    class Config:
        from_attributes = True


# ========== Item Schema ==========

class ItemCreate(BaseModel):
    """创建商品请求"""
    name: str = Field(..., min_length=1, max_length=200, description="商品名称")
    category_id: Optional[int] = Field(None, description="分类ID")
    unit: Optional[str] = Field(None, max_length=20, description="计量单位")
    description: Optional[str] = Field(None, description="商品描述")
    skus: List[SkuCreate] = Field(default_factory=list, description="SKU列表")
    barcodes: List[str] = Field(default_factory=list, description="条码列表")


class ItemUpdate(BaseModel):
    """更新商品请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category_id: Optional[int] = None
    unit: Optional[str] = Field(None, max_length=20)
    status: Optional[int] = Field(None, ge=0, le=1)
    description: Optional[str] = None


class ItemResponse(BaseModel):
    """商品响应"""
    id: int
    sku_id: str
    name: str
    category_id: Optional[int] = None
    unit: Optional[str] = None
    status: int
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    skus: List[SkuResponse] = []
    barcodes: List[BarcodeResponse] = []
    category: Optional[CategoryResponse] = None
    
    class Config:
        from_attributes = True


class ItemBrief(BaseModel):
    """商品简要信息"""
    id: int
    sku_id: str
    name: str
    unit: Optional[str] = None
    status: int
    
    class Config:
        from_attributes = True


# ========== Query Schema ==========

class ItemQuery(PageQuery):
    """商品查询条件"""
    keyword: Optional[str] = Field(None, description="关键词搜索")
    category_id: Optional[int] = Field(None, description="分类ID")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")


# ========== Barcode Bind Schema ==========

class BarcodeBindRequest(BaseModel):
    """条码绑定请求"""
    item_id: int
    barcode: str = Field(..., min_length=1, max_length=50)
    is_primary: bool = False
