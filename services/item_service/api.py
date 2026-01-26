"""
商品中心 - API 路由
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.auth import CurrentUser, get_current_user, require_roles
from erp_common.database import get_db
from erp_common.schemas.base import PageResult, Result
from erp_common.utils.kafka_utils import KafkaProducer
from erp_common.utils.redis_utils import RedisClient, get_redis

from .schemas import (
    BarcodeBindRequest,
    BarcodeResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    ItemCreate,
    ItemQuery,
    ItemResponse,
    ItemUpdate,
)
from .service import CategoryService, ItemService

router = APIRouter(prefix="/item", tags=["商品中心"])


# ==================== 健康检查（必须放在最前面） ====================

@router.get("/health", summary="健康检查")
async def health_check():
    """服务健康检查"""
    return {"status": "healthy", "service": "item-service"}


@router.get("/ready", summary="就绪检查")
async def readiness_check():
    """服务就绪检查"""
    return {"status": "ready", "service": "item-service"}


# 全局 Kafka 生产者（在 lifespan 中初始化）
kafka_producer: KafkaProducer = None


def get_item_service(
    db: AsyncSession = Depends(get_db),
) -> ItemService:
    """获取商品服务实例"""
    return ItemService(db, redis=None, kafka=kafka_producer)


def get_category_service(
    db: AsyncSession = Depends(get_db),
) -> CategoryService:
    """获取分类服务实例"""
    return CategoryService(db)


# ==================== 商品接口 ====================

@router.post("/create", response_model=Result[ItemResponse], summary="创建商品")
async def create_item(
    data: ItemCreate,
    service: ItemService = Depends(get_item_service),
    user: CurrentUser = Depends(get_current_user),
):
    """
    创建商品
    
    - **name**: 商品名称（必填）
    - **category_id**: 分类ID
    - **unit**: 计量单位
    - **skus**: SKU列表
    - **barcodes**: 条码列表
    """
    item = await service.create_item(data, operator=user.username)
    return Result.ok(data=ItemResponse.model_validate(item))


@router.get("/{item_id}", response_model=Result[ItemResponse], summary="获取商品详情")
async def get_item(
    item_id: int,
    service: ItemService = Depends(get_item_service),
    user: CurrentUser = Depends(get_current_user),
):
    """根据ID获取商品详情"""
    item = await service.get_item(item_id)
    return Result.ok(data=ItemResponse.model_validate(item))


@router.get("/sku/{sku_id}", response_model=Result[ItemResponse], summary="通过SKU获取商品")
async def get_item_by_sku(
    sku_id: str,
    service: ItemService = Depends(get_item_service),
    user: CurrentUser = Depends(get_current_user),
):
    """根据 SKU ID 获取商品详情"""
    item = await service.get_item_by_sku(sku_id)
    return Result.ok(data=ItemResponse.model_validate(item))


@router.get("/barcode/{barcode}", response_model=Result[ItemResponse], summary="通过条码获取商品")
async def get_item_by_barcode(
    barcode: str,
    service: ItemService = Depends(get_item_service),
    user: CurrentUser = Depends(get_current_user),
):
    """根据条码获取商品详情（用于 POS 扫码）"""
    item = await service.get_item_by_barcode(barcode)
    return Result.ok(data=ItemResponse.model_validate(item))


@router.put("/{item_id}", response_model=Result[ItemResponse], summary="更新商品")
async def update_item(
    item_id: int,
    data: ItemUpdate,
    service: ItemService = Depends(get_item_service),
    user: CurrentUser = Depends(get_current_user),
):
    """更新商品信息"""
    item = await service.update_item(item_id, data, operator=user.username)
    return Result.ok(data=ItemResponse.model_validate(item))


@router.get("/list", response_model=Result[PageResult[ItemResponse]], summary="商品列表")
async def list_items(
    keyword: str = Query(None, description="关键词搜索"),
    category_id: int = Query(None, description="分类ID"),
    status: int = Query(None, ge=0, le=1, description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: ItemService = Depends(get_item_service),
    user: CurrentUser = Depends(get_current_user),
):
    """分页查询商品列表"""
    query = ItemQuery(
        keyword=keyword,
        category_id=category_id,
        status=status,
        page=page,
        size=size,
    )
    result = await service.list_items(query)
    return Result.ok(data=result)


@router.post("/barcode/bind", response_model=Result[BarcodeResponse], summary="绑定条码")
async def bind_barcode(
    request: BarcodeBindRequest,
    service: ItemService = Depends(get_item_service),
    user: CurrentUser = Depends(get_current_user),
):
    """将条码绑定到商品"""
    barcode = await service.bind_barcode(request)
    return Result.ok(data=BarcodeResponse.model_validate(barcode))


# ==================== 分类接口 ====================

@router.post("/category/create", response_model=Result[CategoryResponse], summary="创建分类")
async def create_category(
    data: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
    user: CurrentUser = Depends(require_roles("ADMIN", "STORE_MANAGER")),
):
    """创建商品分类（需要管理员权限）"""
    category = await service.create_category(data)
    return Result.ok(data=CategoryResponse.model_validate(category))


@router.get("/category/{category_id}", response_model=Result[CategoryResponse], summary="获取分类")
async def get_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
    user: CurrentUser = Depends(get_current_user),
):
    """获取分类详情"""
    category = await service.get_category(category_id)
    return Result.ok(data=CategoryResponse.model_validate(category))


@router.get("/category/list", response_model=Result[list[CategoryResponse]], summary="分类列表")
async def list_categories(
    parent_id: int = Query(0, description="父分类ID，0表示顶级分类"),
    service: CategoryService = Depends(get_category_service),
    user: CurrentUser = Depends(get_current_user),
):
    """获取分类列表"""
    categories = await service.list_categories(parent_id)
    return Result.ok(data=[CategoryResponse.model_validate(c) for c in categories])
