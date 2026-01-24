"""库存中心 - REST API 路由"""
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.database import get_db
from erp_common.schemas.base import Result, PageResult
from erp_common.auth import get_current_user, CurrentUser
from erp_common.utils.kafka_utils import get_kafka_producer, KafkaProducer
from erp_common.utils.redis_utils import get_redis_client, RedisClient

from .service import StockService
from .schemas import (
    StockInRequest, StockInResponse,
    StockOutRequest, StockOutResponse,
    StockLockRequest, StockLockResponse,
    StockUnlockRequest, StockUnlockResponse,
    StockWithDetails, StockMoveResponse, StockMoveQuery,
    MoveType, SourceType
)

router = APIRouter(prefix="/stock", tags=["库存管理"])


def get_stock_service(
    db: AsyncSession = Depends(get_db),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer),
    redis: Optional[RedisClient] = Depends(get_redis_client)
) -> StockService:
    return StockService(db, kafka, redis)


# ============ 入库接口 ============

@router.post("/in", response_model=Result[StockInResponse], summary="库存入库")
async def stock_in(
    request: StockInRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: StockService = Depends(get_stock_service)
):
    """
    库存入库
    - 支持批量入库多个 SKU
    - 自动计算移动加权平均成本
    - 记录批次明细和库存流水
    """
    result = await service.stock_in(request, operator=current_user.username)
    return Result.ok(data=result)


# ============ 出库接口 ============

@router.post("/out", response_model=Result[StockOutResponse], summary="库存出库")
async def stock_out(
    request: StockOutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: StockService = Depends(get_stock_service)
):
    """
    库存出库
    - 支持批量出库多个 SKU
    - FIFO 扣减批次明细
    - 校验可用库存
    """
    result = await service.stock_out(request, operator=current_user.username)
    return Result.ok(data=result)


# ============ 锁定/解锁接口 ============

@router.post("/lock", response_model=Result[StockLockResponse], summary="锁定库存")
async def lock_stock(
    request: StockLockRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: StockService = Depends(get_stock_service)
):
    """
    锁定库存
    - 用于订单创建时锁定库存
    - 锁定后可用库存减少，实际库存不变
    """
    result = await service.lock_stock(request, operator=current_user.username)
    return Result.ok(data=result)


@router.post("/unlock", response_model=Result[StockUnlockResponse], summary="解锁库存")
async def unlock_stock(
    request: StockUnlockRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: StockService = Depends(get_stock_service)
):
    """
    解锁库存
    - 用于订单取消时解锁库存
    - 可按锁定单号或来源单号解锁
    """
    result = await service.unlock_stock(request, operator=current_user.username)
    return Result.ok(data=result)


@router.post("/consume/{order_no}", response_model=Result[StockOutResponse], summary="消耗锁定库存")
async def consume_locked_stock(
    order_no: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: StockService = Depends(get_stock_service)
):
    """
    消耗锁定库存
    - 用于订单支付后出库
    - 自动查找订单的锁定记录并执行出库
    """
    result = await service.consume_locked_stock(order_no, operator=current_user.username)
    return Result.ok(data=result)


# ============ 查询接口 ============

@router.get("/{sku_id}", response_model=Result[StockWithDetails], summary="查询库存详情")
async def get_stock_info(
    sku_id: str,
    warehouse_id: int = Query(..., description="仓库ID"),
    service: StockService = Depends(get_stock_service)
):
    """
    查询库存详情
    - 包含库存主表信息
    - 包含批次明细信息
    """
    result = await service.get_stock_info(sku_id, warehouse_id)
    if not result:
        return Result.fail(code="STOCK_NOT_FOUND", message="库存记录不存在")
    return Result.ok(data=result)


@router.get("/moves/list", response_model=Result[PageResult[StockMoveResponse]], summary="查询库存流水")
async def query_stock_moves(
    sku_id: Optional[str] = Query(None, description="SKU ID"),
    warehouse_id: Optional[int] = Query(None, description="仓库ID"),
    move_type: Optional[MoveType] = Query(None, description="流水类型"),
    source_type: Optional[SourceType] = Query(None, description="来源类型"),
    source_order_no: Optional[str] = Query(None, description="来源单号"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: StockService = Depends(get_stock_service)
):
    """
    查询库存流水
    - 支持多条件筛选
    - 支持分页
    """
    query = StockMoveQuery(
        sku_id=sku_id,
        warehouse_id=warehouse_id,
        move_type=move_type,
        source_type=source_type,
        source_order_no=source_order_no,
        page=page,
        page_size=page_size
    )
    items, total = await service.query_stock_moves(query)
    return Result.ok(data=PageResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    ))


# ============ 批量查询接口 ============

@router.post("/batch/query", response_model=Result[list], summary="批量查询库存")
async def batch_query_stock(
    sku_ids: list[str],
    warehouse_id: int = Query(..., description="仓库ID"),
    service: StockService = Depends(get_stock_service)
):
    """
    批量查询库存
    - 一次查询多个 SKU 的库存信息
    """
    results = []
    for sku_id in sku_ids:
        stock_info = await service.get_stock_info(sku_id, warehouse_id)
        if stock_info:
            results.append(stock_info)
    return Result.ok(data=results)
