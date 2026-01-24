"""采购中心 - REST API 路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from erp_common.database import get_db
from erp_common.schemas.base import Result, PageResult
from erp_common.auth import get_current_user, CurrentUser
from erp_common.utils.kafka_utils import get_kafka_producer, KafkaProducer

from .service import SupplierService, PurchaseOrderService
from .schemas import (
    SupplierCreate, SupplierUpdate, SupplierResponse,
    PoOrderCreate, PoOrderUpdate, PoOrderResponse,
    PoApproveRequest, PoReceiveRequest, PoReceiveResponse,
    PoOrderQuery, PoOrderBrief
)

router = APIRouter(prefix="/purchase", tags=["采购管理"])


def get_supplier_service(db: AsyncSession = Depends(get_db)) -> SupplierService:
    return SupplierService(db)


def get_purchase_order_service(
    db: AsyncSession = Depends(get_db),
    kafka: Optional[KafkaProducer] = Depends(get_kafka_producer)
) -> PurchaseOrderService:
    return PurchaseOrderService(db, kafka)


# ============ 供应商管理 ============

@router.post("/supplier", response_model=Result[SupplierResponse], summary="创建供应商")
async def create_supplier(
    request: SupplierCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service)
):
    """创建供应商"""
    supplier = await service.create(request)
    return Result.ok(data=SupplierResponse.model_validate(supplier))


@router.get("/supplier/{supplier_id}", response_model=Result[SupplierResponse], summary="获取供应商")
async def get_supplier(
    supplier_id: int,
    service: SupplierService = Depends(get_supplier_service)
):
    """获取供应商详情"""
    supplier = await service.get_by_id(supplier_id)
    if not supplier:
        return Result.fail(code="NOT_FOUND", message="供应商不存在")
    return Result.ok(data=SupplierResponse.model_validate(supplier))


@router.put("/supplier/{supplier_id}", response_model=Result[SupplierResponse], summary="更新供应商")
async def update_supplier(
    supplier_id: int,
    request: SupplierUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service)
):
    """更新供应商信息"""
    supplier = await service.update(supplier_id, request)
    return Result.ok(data=SupplierResponse.model_validate(supplier))


@router.get("/supplier/list", response_model=Result[PageResult[SupplierResponse]], summary="供应商列表")
async def list_suppliers(
    status: Optional[str] = Query(None, description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: SupplierService = Depends(get_supplier_service)
):
    """供应商列表"""
    suppliers, total = await service.list_suppliers(status=status, page=page, page_size=page_size)
    return Result.ok(data=PageResult(
        items=[SupplierResponse.model_validate(s) for s in suppliers],
        total=total,
        page=page,
        page_size=page_size
    ))


# ============ 采购订单管理 ============

@router.post("/order", response_model=Result[PoOrderResponse], summary="创建采购订单")
async def create_po_order(
    request: PoOrderCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """创建采购订单"""
    order = await service.create(request, created_by=current_user.username)
    return Result.ok(data=PoOrderResponse.model_validate(order))


@router.get("/order/{po_id}", response_model=Result[PoOrderResponse], summary="获取采购订单")
async def get_po_order(
    po_id: int,
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """获取采购订单详情"""
    order = await service.get_by_id(po_id)
    if not order:
        return Result.fail(code="NOT_FOUND", message="采购订单不存在")
    return Result.ok(data=PoOrderResponse.model_validate(order))


@router.put("/order/{po_id}", response_model=Result[PoOrderResponse], summary="更新采购订单")
async def update_po_order(
    po_id: int,
    request: PoOrderUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """更新采购订单"""
    # TODO: 只允许在特定状态下更新
    order = await service.get_by_id(po_id)
    if not order:
        return Result.fail(code="NOT_FOUND", message="采购订单不存在")
    
    # 只允许在草稿状态下更新
    if order.status != "DRAFT":
        return Result.fail(code="INVALID_STATUS", message="只有草稿状态的订单可以修改")
    
    # 更新字段
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    
    await service.db.commit()
    await service.db.refresh(order)
    return Result.ok(data=PoOrderResponse.model_validate(order))


@router.post("/order/{po_id}/submit", response_model=Result[PoOrderResponse], summary="提交审批")
async def submit_po_order(
    po_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """提交采购订单审批"""
    order = await service.submit(po_id)
    return Result.ok(data=PoOrderResponse.model_validate(order))


@router.post("/order/{po_id}/approve", response_model=Result[PoOrderResponse], summary="审批采购订单")
async def approve_po_order(
    po_id: int,
    request: PoApproveRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """审批采购订单"""
    order = await service.approve(po_id, request, current_user.username)
    return Result.ok(data=PoOrderResponse.model_validate(order))


@router.post("/order/{po_id}/cancel", response_model=Result[PoOrderResponse], summary="取消采购订单")
async def cancel_po_order(
    po_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """取消采购订单"""
    order = await service.cancel(po_id)
    return Result.ok(data=PoOrderResponse.model_validate(order))


@router.post("/receive", response_model=Result[PoReceiveResponse], summary="采购收货")
async def receive_po(
    request: PoReceiveRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """采购收货"""
    receive = await service.receive(request, current_user.username)
    return Result.ok(data=receive)


@router.get("/order/list", response_model=Result[PageResult[PoOrderBrief]], summary="采购订单列表")
async def list_po_orders(
    po_no: Optional[str] = Query(None, description="采购单号"),
    supplier_id: Optional[int] = Query(None, description="供应商ID"),
    status: Optional[str] = Query(None, description="状态"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    service: PurchaseOrderService = Depends(get_purchase_order_service)
):
    """采购订单列表"""
    query = PoOrderQuery(
        po_no=po_no,
        supplier_id=supplier_id,
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
