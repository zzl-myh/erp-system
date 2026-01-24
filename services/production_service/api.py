"""生产中心 - REST API 路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.database import get_db
from erp_common.schemas.base import Result, PageResult
from erp_common.auth import get_current_user, CurrentUser
from erp_common.utils.kafka_utils import get_kafka_producer, KafkaProducer

from .service import BomService, ProductionOrderService
from .schemas import (
    BomTemplateCreate, BomTemplateUpdate, BomTemplateResponse,
    MoOrderCreate, MoOrderUpdate, MoOrderResponse,
    MoReleaseRequest, MoStartRequest, MoCompleteRequest,
    MoIssueMaterialRequest, MoConsumeMaterialRequest,
    MoOrderQuery, MoOrderBrief
)

router = APIRouter(prefix="/production", tags=["生产管理"])


def get_bom_service(db: AsyncSession = Depends(get_db)) -> BomService:
    return BomService(db)


def get_production_order_service(
    db: AsyncSession = Depends(get_db),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer)
) -> ProductionOrderService:
    return ProductionOrderService(db, kafka)


# ============ BOM管理 ============

@router.post("/bom", response_model=Result[BomTemplateResponse], summary="创建BOM模板")
async def create_bom(
    request: BomTemplateCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: BomService = Depends(get_bom_service)
):
    """创建BOM模板"""
    bom = await service.create(request)
    return Result.ok(data=BomTemplateResponse.model_validate(bom))


@router.get("/bom/{bom_id}", response_model=Result[BomTemplateResponse], summary="获取BOM模板")
async def get_bom(
    bom_id: int,
    service: BomService = Depends(get_bom_service)
):
    """获取BOM模板详情"""
    bom = await service.get_by_id(bom_id)
    if not bom:
        return Result.fail(code="NOT_FOUND", message="BOM模板不存在")
    return Result.ok(data=BomTemplateResponse.model_validate(bom))


@router.put("/bom/{bom_id}", response_model=Result[BomTemplateResponse], summary="更新BOM模板")
async def update_bom(
    bom_id: int,
    request: BomTemplateUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: BomService = Depends(get_bom_service)
):
    """更新BOM模板"""
    bom = await service.update(bom_id, request)
    return Result.ok(data=BomTemplateResponse.model_validate(bom))


# ============ 生产订单管理 ============

@router.post("/order", response_model=Result[MoOrderResponse], summary="创建生产订单")
async def create_mo_order(
    request: MoOrderCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProductionOrderService = Depends(get_production_order_service)
):
    """创建生产订单"""
    order = await service.create(request, created_by=current_user.username)
    return Result.ok(data=MoOrderResponse.model_validate(order))


@router.get("/order/{mo_id}", response_model=Result[MoOrderResponse], summary="获取生产订单")
async def get_mo_order(
    mo_id: int,
    service: ProductionOrderService = Depends(get_production_order_service)
):
    """获取生产订单详情"""
    order = await service.get_by_id(mo_id)
    if not order:
        return Result.fail(code="NOT_FOUND", message="生产订单不存在")
    return Result.ok(data=MoOrderResponse.model_validate(order))


@router.put("/order/{mo_id}", response_model=Result[MoOrderResponse], summary="更新生产订单")
async def update_mo_order(
    mo_id: int,
    request: MoOrderUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProductionOrderService = Depends(get_production_order_service)
):
    """更新生产订单"""
    order = await service.get_by_id(mo_id)
    if not order:
        return Result.fail(code="NOT_FOUND", message="生产订单不存在")
    
    # 只允许在特定状态下更新
    if order.status not in ["DRAFT", "RELEASED"]:
        return Result.fail(code="INVALID_STATUS", message="当前状态不允许修改")
    
    # 更新字段
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    
    await service.db.commit()
    await service.db.refresh(order)
    return Result.ok(data=MoOrderResponse.model_validate(order))


@router.post("/order/{mo_id}/release", response_model=Result[MoOrderResponse], summary="下达生产订单")
async def release_mo_order(
    mo_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProductionOrderService = Depends(get_production_order_service)
):
    """下达生产订单"""
    order = await service.release(mo_id)
    return Result.ok(data=MoOrderResponse.model_validate(order))


@router.post("/order/{mo_id}/start", response_model=Result[MoOrderResponse], summary="开工生产订单")
async def start_mo_order(
    mo_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProductionOrderService = Depends(get_production_order_service)
):
    """开工生产订单"""
    order = await service.start(mo_id)
    return Result.ok(data=MoOrderResponse.model_validate(order))


@router.post("/order/{mo_id}/complete", response_model=Result[MoOrderResponse], summary="完工生产订单")
async def complete_mo_order(
    mo_id: int,
    request: MoCompleteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProductionOrderService = Depends(get_production_order_service)
):
    """完工生产订单"""
    order = await service.complete(mo_id, request)
    return Result.ok(data=MoOrderResponse.model_validate(order))


@router.post("/order/{mo_id}/issue-material", response_model=Result[MoOrderResponse], summary="发料")
async def issue_material(
    mo_id: int,
    request: MoIssueMaterialRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProductionOrderService = Depends(get_production_order_service)
):
    """发料"""
    order = await service.issue_material(mo_id, request, current_user.username)
    return Result.ok(data=MoOrderResponse.model_validate(order))


@router.post("/order/{mo_id}/consume-material", response_model=Result[MoOrderResponse], summary="消耗物料")
async def consume_material(
    mo_id: int,
    request: MoConsumeMaterialRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProductionOrderService = Depends(get_production_order_service)
):
    """消耗物料"""
    order = await service.consume_material(mo_id, request, current_user.username)
    return Result.ok(data=MoOrderResponse.model_validate(order))


@router.post("/order/{mo_id}/cancel", response_model=Result[MoOrderResponse], summary="取消生产订单")
async def cancel_mo_order(
    mo_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: ProductionOrderService = Depends(get_production_order_service)
):
    """取消生产订单"""
    order = await service.cancel(mo_id)
    return Result.ok(data=MoOrderResponse.model_validate(order))


@router.get("/order/list", response_model=Result[PageResult[MoOrderBrief]], summary="生产订单列表")
async def list_mo_orders(
    mo_no: Optional[str] = Query(None, description="生产单号"),
    product_sku_id: Optional[str] = Query(None, description="成品SKU ID"),
    status: Optional[str] = Query(None, description="状态"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: ProductionOrderService = Depends(get_production_order_service)
):
    """生产订单列表"""
    query = MoOrderQuery(
        mo_no=mo_no,
        product_sku_id=product_sku_id,
        status=status,
        page=page,
        page_size=page_size
    )
    
    # 转换日期字符串为 date 对象
    if start_date:
        from datetime import datetime
        query.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if end_date:
        from datetime import datetime
        query.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    orders, total = await service.query(query)
    return Result.ok(data=PageResult(
        items=orders,
        total=total,
        page=page,
        page_size=page_size
    ))
