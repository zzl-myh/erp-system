"""
商品中心 - 业务服务层
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.exceptions import ConflictError, NotFoundError
from erp_common.schemas.base import PageResult
from erp_common.schemas.events import ItemCreatedEvent, ItemUpdatedEvent
from erp_common.utils.kafka_utils import KafkaProducer, KafkaTopics
from erp_common.utils.redis_utils import RedisClient

from .models import Item, ItemBarcode, ItemCategory, ItemSku
from .schemas import (
    BarcodeBindRequest,
    CategoryCreate,
    CategoryUpdate,
    ItemCreate,
    ItemQuery,
    ItemResponse,
    ItemUpdate,
)

logger = logging.getLogger(__name__)


class SkuIdGenerator:
    """
    SKU ID 生成器
    
    格式: {类目前缀2位}{年月4位}{序列号6位}
    示例: SP202401000001
    """
    
    def __init__(self, redis: RedisClient):
        self.redis = redis
        self.prefix = "SP"  # 默认前缀
    
    async def generate(self, category_prefix: str = None) -> str:
        """生成唯一 SKU ID"""
        prefix = category_prefix or self.prefix
        date_part = datetime.now().strftime("%Y%m")
        
        # 使用 Redis INCR 生成序列号
        key = f"sku_seq:{prefix}:{date_part}"
        seq = await self.redis.incr(key)
        
        # 设置过期时间（下个月自动清理）
        if seq == 1:
            # 首次生成，设置31天过期
            await self.redis.set(key, str(seq), expire=31 * 24 * 3600)
        
        return f"{prefix}{date_part}{seq:06d}"


class ItemService:
    """商品服务"""
    
    def __init__(
        self, 
        db: AsyncSession, 
        redis: Optional[RedisClient] = None,
        kafka: Optional[KafkaProducer] = None
    ):
        self.db = db
        self.redis = redis
        self.kafka = kafka
        self.sku_generator = SkuIdGenerator(redis) if redis else None
    
    async def create_item(self, data: ItemCreate, operator: str = None) -> Item:
        """
        创建商品
        
        Args:
            data: 创建商品请求数据
            operator: 操作人
        
        Returns:
            创建的商品对象
        """
        # 1. 生成 SKU ID
        if self.sku_generator:
            sku_id = await self.sku_generator.generate()
        else:
            # 简单生成（测试用）
            import uuid
            sku_id = f"SP{uuid.uuid4().hex[:12].upper()}"
        
        # 2. 创建商品
        item = Item(
            sku_id=sku_id,
            name=data.name,
            category_id=data.category_id,
            unit=data.unit,
            description=data.description,
            status=1,
        )
        self.db.add(item)
        await self.db.flush()
        
        # 3. 创建 SKU
        for i, sku_data in enumerate(data.skus):
            sku = ItemSku(
                item_id=item.id,
                sku_id=f"{sku_id}-{i+1:02d}" if i > 0 else sku_id,
                spec_info=sku_data.spec_info,
                price=sku_data.price,
                cost=sku_data.cost,
            )
            self.db.add(sku)
        
        # 如果没有 SKU，创建默认 SKU
        if not data.skus:
            default_sku = ItemSku(
                item_id=item.id,
                sku_id=sku_id,
            )
            self.db.add(default_sku)
        
        # 4. 创建条码
        for i, barcode in enumerate(data.barcodes):
            barcode_obj = ItemBarcode(
                item_id=item.id,
                sku_id=sku_id,
                barcode=barcode,
                is_primary=1 if i == 0 else 0,
            )
            self.db.add(barcode_obj)
        
        await self.db.flush()
        
        # 5. 发布事件
        if self.kafka:
            event = ItemCreatedEvent(
                aggregate_id=str(item.id),
                operator=operator,
                payload={
                    "id": item.id,
                    "sku_id": item.sku_id,
                    "name": item.name,
                }
            )
            await self.kafka.send(KafkaTopics.ITEM_EVENTS, event)
        
        logger.info(f"Item created: {item.sku_id} - {item.name}")
        return item
    
    async def get_item(self, item_id: int) -> Item:
        """获取商品详情"""
        result = await self.db.execute(
            select(Item).where(Item.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise NotFoundError("Item", item_id)
        
        return item
    
    async def get_item_by_sku(self, sku_id: str) -> Item:
        """通过 SKU ID 获取商品"""
        result = await self.db.execute(
            select(Item).where(Item.sku_id == sku_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise NotFoundError("Item", sku_id)
        
        return item
    
    async def get_item_by_barcode(self, barcode: str) -> Item:
        """通过条码获取商品"""
        result = await self.db.execute(
            select(Item)
            .join(ItemBarcode, Item.id == ItemBarcode.item_id)
            .where(ItemBarcode.barcode == barcode)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise NotFoundError("Item", f"barcode:{barcode}")
        
        return item
    
    async def update_item(
        self, 
        item_id: int, 
        data: ItemUpdate,
        operator: str = None
    ) -> Item:
        """更新商品"""
        item = await self.get_item(item_id)
        
        # 更新字段
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        
        await self.db.flush()
        
        # 发布事件
        if self.kafka:
            event = ItemUpdatedEvent(
                aggregate_id=str(item.id),
                operator=operator,
                payload={
                    "id": item.id,
                    "sku_id": item.sku_id,
                    "updated_fields": list(update_data.keys()),
                }
            )
            await self.kafka.send(KafkaTopics.ITEM_EVENTS, event)
        
        logger.info(f"Item updated: {item.sku_id}")
        return item
    
    async def list_items(self, query: ItemQuery) -> PageResult[ItemResponse]:
        """分页查询商品列表"""
        # 构建查询条件
        conditions = []
        
        if query.keyword:
            conditions.append(
                or_(
                    Item.name.contains(query.keyword),
                    Item.sku_id.contains(query.keyword),
                )
            )
        
        if query.category_id is not None:
            conditions.append(Item.category_id == query.category_id)
        
        if query.status is not None:
            conditions.append(Item.status == query.status)
        
        # 查询总数
        count_stmt = select(func.count(Item.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar()
        
        # 查询数据
        stmt = select(Item).order_by(Item.id.desc())
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.offset(query.offset).limit(query.size)
        
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        
        return PageResult(
            items=[ItemResponse.model_validate(item) for item in items],
            total=total,
            page=query.page,
            size=query.size,
        )
    
    async def bind_barcode(self, request: BarcodeBindRequest) -> ItemBarcode:
        """绑定条码到商品"""
        # 检查商品是否存在
        item = await self.get_item(request.item_id)
        
        # 检查条码是否已存在
        existing = await self.db.execute(
            select(ItemBarcode).where(ItemBarcode.barcode == request.barcode)
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Barcode {request.barcode} already exists")
        
        # 创建条码
        barcode = ItemBarcode(
            item_id=item.id,
            sku_id=item.sku_id,
            barcode=request.barcode,
            is_primary=1 if request.is_primary else 0,
        )
        self.db.add(barcode)
        await self.db.flush()
        
        logger.info(f"Barcode bound: {request.barcode} -> {item.sku_id}")
        return barcode


class CategoryService:
    """分类服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_category(self, data: CategoryCreate) -> ItemCategory:
        """创建分类"""
        # 计算层级
        level = 1
        if data.parent_id > 0:
            parent = await self.db.get(ItemCategory, data.parent_id)
            if parent:
                level = parent.level + 1
        
        category = ItemCategory(
            name=data.name,
            parent_id=data.parent_id,
            level=level,
            sort_order=data.sort_order,
        )
        self.db.add(category)
        await self.db.flush()
        
        return category
    
    async def get_category(self, category_id: int) -> ItemCategory:
        """获取分类"""
        category = await self.db.get(ItemCategory, category_id)
        if not category:
            raise NotFoundError("Category", category_id)
        return category
    
    async def list_categories(self, parent_id: int = 0) -> List[ItemCategory]:
        """获取分类列表"""
        result = await self.db.execute(
            select(ItemCategory)
            .where(ItemCategory.parent_id == parent_id)
            .order_by(ItemCategory.sort_order)
        )
        return list(result.scalars().all())
